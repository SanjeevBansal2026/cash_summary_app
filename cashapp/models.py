from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class Brand(models.Model):
    name=models.CharField(max_length=100, unique=True)
    active=models.BooleanField(default=True)
    def __str__(self): return self.name

class Location(models.Model):
    name=models.CharField(max_length=120)
    code=models.CharField(max_length=30, blank=True)
    active=models.BooleanField(default=True)
    class Meta: unique_together=('name','code')
    def __str__(self): return self.name

class User(AbstractUser):
    ROLE_CHOICES=(('superuser','Super User'),('manager','Manager'),('cashier','Cashier'))
    role=models.CharField(max_length=20, choices=ROLE_CHOICES, default='cashier')
    brands=models.ManyToManyField(Brand, blank=True, related_name='assigned_users')
    locations=models.ManyToManyField(Location, blank=True, related_name='assigned_users')
    managers=models.ManyToManyField('self', blank=True, symmetrical=False, related_name='assigned_cashiers', limit_choices_to={'role':'manager'})
    def save(self,*args,**kwargs):
        if self.is_superuser: self.role='superuser'
        super().save(*args,**kwargs)
    def __str__(self): return self.get_full_name() or self.username

class CashEntry(models.Model):
    CASH_TYPES=(('main','Main Cash'),('petty','Petty Cash'))
    STATUS=(('pending','Pending'),('approved','Approved'),('revised','Revised'),('rejected','Rejected'))
    cashier=models.ForeignKey(User,on_delete=models.PROTECT,related_name='cash_entries')
    brand=models.ForeignKey(Brand,on_delete=models.PROTECT)
    location=models.ForeignKey(Location,on_delete=models.PROTECT)
    entry_date=models.DateField(default=timezone.localdate)
    cash_type=models.CharField(max_length=10,choices=CASH_TYPES)
    opening=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    today_deposit=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    today_collection=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    transfer_to_petty=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    received_from_main=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    expenses=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    calculated_closing=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    denomination_total=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    difference=models.DecimalField(max_digits=14,decimal_places=2,default=0)
    status=models.CharField(max_length=12,choices=STATUS,default='pending')
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    submitted_at=models.DateTimeField(null=True,blank=True)
    last_action_by=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name='cash_actions')
    last_action_at=models.DateTimeField(null=True,blank=True)
    manager_note=models.TextField(blank=True)
    class Meta: ordering=['-entry_date','-created_at']; unique_together=('cashier','brand','location','entry_date','cash_type')
    def calculate(self):
        if self.cash_type=='main':
            return self.opening + self.today_collection - self.today_deposit - self.transfer_to_petty
        return self.opening + self.received_from_main - self.expenses
    def save(self,*args,**kwargs):
        self.calculated_closing=self.calculate(); self.difference=self.calculated_closing-self.denomination_total
        super().save(*args,**kwargs)
    def __str__(self): return f'{self.cashier} | {self.entry_date} | {self.get_cash_type_display()}'

class Denomination(models.Model):
    entry=models.ForeignKey(CashEntry,on_delete=models.CASCADE,related_name='denominations')
    value=models.PositiveIntegerField()
    quantity=models.PositiveIntegerField(default=0)
    @property
    def amount(self): return self.value*self.quantity

class Attachment(models.Model):
    TYPES=(('deposit_slip','Deposit Slip'),('cashbook','Cashbook'),('bank_statement','Bank Statement'),('other','Other'))
    entry=models.ForeignKey(CashEntry,on_delete=models.CASCADE,related_name='attachments')
    attachment_type=models.CharField(max_length=30,choices=TYPES)
    file=models.FileField(upload_to='cash_attachments/%Y/%m/%d/')
    uploaded_at=models.DateTimeField(auto_now_add=True)

class ApprovalHistory(models.Model):
    ACTIONS=(('submitted','Submitted'),('approved','Approved'),('revised','Revised'),('rejected','Rejected'),('edited','Edited'))
    entry=models.ForeignKey(CashEntry,on_delete=models.CASCADE,related_name='history')
    actor=models.ForeignKey(User,on_delete=models.PROTECT)
    action=models.CharField(max_length=20,choices=ACTIONS)
    note=models.TextField(blank=True)
    at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-at']
