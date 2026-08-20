from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import CashEntryForm, AttachmentForm, ReviewForm
from .models import CashEntry, Denomination, Attachment, ApprovalHistory, Brand, Location, User
DENOMS=[500,200,100,50,20,10,5,2,1]

def scoped_entries(user):
    qs=CashEntry.objects.select_related('cashier','brand','location','last_action_by')
    if user.is_superuser or user.role=='superuser': return qs
    if user.role=='manager': return qs.filter(cashier__in=user.assigned_cashiers.all())
    return qs.filter(cashier=user)

@never_cache
def login_view(request):
    if request.user.is_authenticated: return redirect('dashboard')
    if request.method=='POST':
        user=authenticate(request,username=request.POST.get('username'),password=request.POST.get('password'))
        if user: login(request,user); return redirect('dashboard')
        messages.error(request,'Invalid username or password.')
    return render(request,'registration/login.html')

def logout_view(request):
    logout(request)
    response = redirect('login')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

@login_required
@never_cache
def dashboard(request):
    qs=scoped_entries(request.user)
    context={'counts':qs.values('status').annotate(n=Count('id')),'total_entries':qs.count(),'total_difference':qs.aggregate(x=Sum('difference'))['x'] or 0,'total_closing':qs.aggregate(x=Sum('calculated_closing'))['x'] or 0}
    if request.user.role in ('superuser','manager') or request.user.is_superuser:
        context['cashiers']=User.objects.filter(role='cashier').prefetch_related('brands','locations','managers') if request.user.role in ('superuser',) or request.user.is_superuser else request.user.assigned_cashiers.all().prefetch_related('brands','locations','managers')
    return render(request,'cashapp/dashboard.html',context)

@login_required
@never_cache
def entry_list(request):
    qs=scoped_entries(request.user)
    for key in ['status','cash_type','brand','location','cashier']:
        val=request.GET.get(key)
        if val: qs=qs.filter(**{key:val})
    return render(request,'cashapp/entry_list.html',{'entries':qs[:300],'brands':Brand.objects.filter(active=True),'locations':Location.objects.filter(active=True)})

@login_required
@never_cache
def entry_create(request):
    if request.user.role!='cashier' and not request.user.is_superuser: return redirect('entry_list')
    if request.method=='POST':
        form=CashEntryForm(request.POST,user=request.user)
        if form.is_valid():
            e=form.save(commit=False); e.cashier=request.user; e.submitted_at=timezone.now(); e.status='pending'; e.save()
            for d in DENOMS: Denomination.objects.create(entry=e,value=d,quantity=int(request.POST.get(f'denom_{d}',0) or 0))
            e.denomination_total=sum(x.value*x.quantity for x in e.denominations.all()); e.difference=e.calculated_closing-e.denomination_total; e.save(update_fields=['denomination_total','difference','updated_at'])
            for f in ['deposit_slip','cashbook','bank_statement']:
                if request.FILES.get(f): Attachment.objects.create(entry=e,attachment_type=f,file=request.FILES[f])
            ApprovalHistory.objects.create(entry=e,actor=request.user,action='submitted'); messages.success(request,'Cash entry submitted successfully.'); return redirect('entry_detail',e.pk)
    else: form=CashEntryForm(user=request.user)
    return render(request,'cashapp/entry_form.html',{'form':form,'denoms':DENOMS,'title':'New Cash Summary'})

@login_required
@never_cache
def entry_detail(request,pk):
    e=get_object_or_404(scoped_entries(request.user),pk=pk)
    return render(request,'cashapp/entry_detail.html',{'entry':e,'review_form':ReviewForm() if request.user.role=='manager' or request.user.is_superuser else None})

@login_required
@never_cache
def entry_edit(request,pk):
    e=get_object_or_404(CashEntry,pk=pk)
    if request.user!=e.cashier and not request.user.is_superuser: return redirect('entry_detail',pk)
    if e.status not in ('revised',) and not request.user.is_superuser:
        messages.error(request,'Only Revised entries can be edited and resubmitted.'); return redirect('entry_detail',pk)
    if request.method=='POST':
        form=CashEntryForm(request.POST,user=request.user,instance=e)
        if form.is_valid():
            e=form.save(commit=False); e.status='pending'; e.submitted_at=timezone.now(); e.last_action_by=request.user; e.last_action_at=timezone.now(); e.save()
            for d in DENOMS:
                Denomination.objects.update_or_create(entry=e,value=d,defaults={'quantity':int(request.POST.get(f'denom_{d}',0) or 0)})
            e.denomination_total=sum(x.value*x.quantity for x in e.denominations.all()); e.difference=e.calculated_closing-e.denomination_total; e.save(update_fields=['denomination_total','difference','updated_at'])
            for f in ['deposit_slip','cashbook','bank_statement']:
                if request.FILES.get(f): Attachment.objects.create(entry=e,attachment_type=f,file=request.FILES[f])
            ApprovalHistory.objects.create(entry=e,actor=request.user,action='submitted',note='Resubmitted after revision'); messages.success(request,'Revised entry resubmitted.'); return redirect('entry_detail',pk)
    else:
        form=CashEntryForm(user=request.user,instance=e)
    den={d.value:d.quantity for d in e.denominations.all()}
    return render(request,'cashapp/entry_form.html',{'form':form,'denoms':DENOMS,'den':den,'title':'Edit Revised Entry','entry':e})

@login_required
@never_cache
def entry_review(request,pk):
    if request.user.role!='manager' and not request.user.is_superuser: return redirect('entry_detail',pk)
    e=get_object_or_404(CashEntry,pk=pk)
    allowed=request.user.is_superuser or e.cashier in request.user.assigned_cashiers.all()
    if not allowed: messages.error(request,'You do not have access to this employee.'); return redirect('entry_list')
    if request.method=='POST':
        f=ReviewForm(request.POST)
        if f.is_valid():
            e.status=f.cleaned_data['status']; e.manager_note=f.cleaned_data['note']; e.last_action_by=request.user; e.last_action_at=timezone.now(); e.save(update_fields=['status','manager_note','last_action_by','last_action_at','updated_at'])
            ApprovalHistory.objects.create(entry=e,actor=request.user,action=e.status,note=e.manager_note); messages.success(request,f'Entry marked {e.get_status_display()}.')
    return redirect('entry_detail',pk)
