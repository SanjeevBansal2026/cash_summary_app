from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin import AdminSite
from django.db.models import Count, Sum
from django.urls import reverse
from django.utils.html import format_html
from .models import User, Brand, Location, CashEntry, Denomination, Attachment, ApprovalHistory

class CashAdminSite(AdminSite):
    site_header = "CashFlow Control Center"
    site_title = "CashFlow Admin"
    index_title = "Administration & Master Control"
    index_template = "admin/index.html"
    login_template = "admin/login.html"

    def has_permission(self, request):
        return bool(request.user and request.user.is_active and request.user.is_superuser)

    def each_context(self, request):
        context = super().each_context(request)
        entries = CashEntry.objects.all()
        context.update({
            "cashflow_stats": {
                "employees": User.objects.filter(role="cashier").count(),
                "managers": User.objects.filter(role="manager").count(),
                "pending": entries.filter(status="pending").count(),
                "approved": entries.filter(status="approved").count(),
                "revised": entries.filter(status="revised").count(),
                "rejected": entries.filter(status="rejected").count(),
                "collection": entries.aggregate(v=Sum("today_collection"))["v"] or 0,
                "deposit": entries.aggregate(v=Sum("today_deposit"))["v"] or 0,
                "expenses": entries.aggregate(v=Sum("expenses"))["v"] or 0,
                "difference": entries.aggregate(v=Sum("difference"))["v"] or 0,
            },
            "cashflow_recent": entries.select_related("cashier", "brand", "location", "last_action_by")[:8],
        })
        return context

cash_admin_site = CashAdminSite(name="cash_admin")

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("CashFlow Access", {"fields": ("role", "brands", "locations", "managers")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("CashFlow Access", {"fields": ("role", "brands", "locations", "managers")}),)
    list_display = ("user_identity", "role_badge", "allocation_summary", "is_active")
    list_filter = ("role", "is_active", "brands", "locations")
    search_fields = ("username", "first_name", "last_name", "email")

    @admin.display(description="User")
    def user_identity(self, obj):
        return format_html('<strong>{}</strong><br><span class="cf-muted">{}</span>', obj.get_full_name() or obj.username, obj.email or "No email")

    @admin.display(description="Role")
    def role_badge(self, obj):
        label = obj.get_role_display()
        cls = {"cashier": "cashier", "manager": "manager", "superuser": "super"}.get(obj.role, "default")
        return format_html('<span class="cf-badge cf-{}">{}</span>', cls, label)

    @admin.display(description="Allocation")
    def allocation_summary(self, obj):
        return format_html('{} brands · {} locations · {} managers', obj.brands.count(), obj.locations.count(), obj.managers.count())

class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "active_badge", "user_count")
    list_filter = ("active",)
    search_fields = ("name",)
    @admin.display(description="Status")
    def active_badge(self, obj):
        return format_html('<span class="cf-badge cf-{}">{}</span>', "approved" if obj.active else "rejected", "Active" if obj.active else "Inactive")
    @admin.display(description="Assigned users")
    def user_count(self, obj): return obj.assigned_users.count()

class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "active_badge", "user_count")
    list_filter = ("active",)
    search_fields = ("name", "code")
    @admin.display(description="Status")
    def active_badge(self, obj):
        return format_html('<span class="cf-badge cf-{}">{}</span>', "approved" if obj.active else "rejected", "Active" if obj.active else "Inactive")
    @admin.display(description="Assigned users")
    def user_count(self, obj): return obj.assigned_users.count()

class CashEntryAdmin(admin.ModelAdmin):
    list_display = ("entry_identity", "cashier", "brand", "location", "cash_type", "closing_summary", "difference_badge", "status_badge", "last_action_by")
    list_filter = ("cash_type", "status", "brand", "location", "entry_date")
    search_fields = ("cashier__username", "cashier__first_name", "cashier__last_name", "brand__name", "location__name")
    date_hierarchy = "entry_date"
    readonly_fields = ("calculated_closing", "denomination_total", "difference", "created_at", "updated_at", "submitted_at", "last_action_at")
    list_per_page = 25

    @admin.display(description="Entry")
    def entry_identity(self, obj): return format_html('<strong>{}</strong><br><span class="cf-muted">{}</span>', obj.entry_date, obj.get_cash_type_display())
    @admin.display(description="Closing")
    def closing_summary(self, obj): return format_html('₹{:,.2f}<br><span class="cf-muted">Denom ₹{:,.2f}</span>', obj.calculated_closing, obj.denomination_total)
    @admin.display(description="Difference")
    def difference_badge(self, obj):
        cls = "approved" if obj.difference == 0 else "rejected"
        return format_html('<span class="cf-badge cf-{}">₹{:,.2f}</span>', cls, obj.difference)
    @admin.display(description="Status")
    def status_badge(self, obj):
        return format_html('<span class="cf-badge cf-{}">{}</span>', obj.status, obj.get_status_display())

class DenominationAdmin(admin.ModelAdmin):
    list_display = ("entry", "value", "quantity", "amount")
    list_filter = ("value",)
    search_fields = ("entry__cashier__username",)

class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("entry", "attachment_type", "file_link", "uploaded_at")
    list_filter = ("attachment_type", "uploaded_at")
    search_fields = ("entry__cashier__username",)
    @admin.display(description="File")
    def file_link(self, obj):
        return format_html('<a class="cf-file" href="{}" target="_blank">View attachment ↗</a>', obj.file.url) if obj.file else "—"

class ApprovalHistoryAdmin(admin.ModelAdmin):
    list_display = ("entry", "actor", "action_badge", "note", "at")
    list_filter = ("action", "at")
    search_fields = ("actor__username", "entry__cashier__username", "note")
    readonly_fields = ("at",)
    @admin.display(description="Action")
    def action_badge(self, obj): return format_html('<span class="cf-badge cf-{}">{}</span>', obj.action, obj.get_action_display())

for model, model_admin in [
    (User, CustomUserAdmin), (Brand, BrandAdmin), (Location, LocationAdmin),
    (CashEntry, CashEntryAdmin), (Denomination, DenominationAdmin),
    (Attachment, AttachmentAdmin), (ApprovalHistory, ApprovalHistoryAdmin)
]:
    cash_admin_site.register(model, model_admin)
