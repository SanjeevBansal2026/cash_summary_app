from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import CashEntry, Denomination, Attachment, Brand, Location

class CashEntryForm(forms.ModelForm):
    class Meta:
        model=CashEntry
        fields=['cash_type','brand','location','entry_date','opening','today_deposit','today_collection','transfer_to_petty','received_from_main','expenses']
        widgets={'entry_date':forms.DateInput(attrs={'type':'date'}),'opening':forms.NumberInput(attrs={'step':'0.01'}),'today_deposit':forms.NumberInput(attrs={'step':'0.01'}),'today_collection':forms.NumberInput(attrs={'step':'0.01'}),'transfer_to_petty':forms.NumberInput(attrs={'step':'0.01'}),'received_from_main':forms.NumberInput(attrs={'step':'0.01'}),'expenses':forms.NumberInput(attrs={'step':'0.01'})}
    def __init__(self,*args,user=None,instance=None,**kwargs):
        super().__init__(*args,instance=instance,**kwargs)
        if user and user.role=='cashier':
            self.fields['brand'].queryset=user.brands.filter(active=True); self.fields['location'].queryset=user.locations.filter(active=True)
        if instance and instance.cash_type=='main':
            self.fields['received_from_main'].disabled=True; self.fields['expenses'].disabled=True
        elif instance and instance.cash_type=='petty':
            for f in ['today_deposit','today_collection','transfer_to_petty']: self.fields[f].disabled=True
    def clean(self):
        d=super().clean(); t=d.get('cash_type')
        if t=='main':
            for f in ['received_from_main','expenses']: d[f]=0
        elif t=='petty':
            for f in ['today_deposit','today_collection','transfer_to_petty']: d[f]=0
        return d

class AttachmentForm(forms.ModelForm):
    class Meta:
        model=Attachment; fields=['attachment_type','file']

class ReviewForm(forms.Form):
    status=forms.ChoiceField(choices=[('approved','Approve'),('revised','Revised'),('rejected','Reject')])
    note=forms.CharField(required=False,widget=forms.Textarea(attrs={'rows':3,'placeholder':'Manager note'}))
