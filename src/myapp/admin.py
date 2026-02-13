from django.contrib import admin
from django.utils.html import format_html

from .models import (
    ActivityLog,
    AuditLog,
    Event,
    MonthlyAnalytics,
    Notification,
    Payment,
    Reminder,
    Renewal,
    Subscription,
    SubscriptionPlan,
    User,
)

# =============================================================================
# USER MANAGEMENT
# =============================================================================


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "user_id",
        "full_name",
        "email",
        "role",
        "is_active_status",
        "created_at",
    )
    list_filter = ("role", "is_active", "is_deleted")
    search_fields = ("full_name", "email", "organization")
    readonly_fields = ("user_id", "created_at", "updated_at", "password")

    fieldsets = (
        ("Basic Information", {"fields": ("full_name", "email", "role", "password")}),
        (
            "Organization Details",
            {
                "fields": (
                    "organization",
                    "phone",
                    "address",
                    "state",
                    "zipcode",
                    "country",
                    "logo_path",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "SMTP Settings",
            {
                "fields": (
                    "use_user_smtp",
                    "smtp_host",
                    "smtp_port",
                    "smtp_host_user",
                    "smtp_host_password",
                    "smtp_use_tls",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "System Fields",
            {
                "fields": (
                    "is_active",
                    "is_deleted",
                    "created_by",
                    "updated_by",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def is_active_status(self, obj):
        if obj.is_active == 1:
            return format_html('<span style="color: green;">Active</span>')
        return format_html('<span style="color: red;">Inactive</span>')

    is_active_status.short_description = "Status"


# =============================================================================
# SUBSCRIPTION MANAGEMENT
# =============================================================================


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "monthly_price",
        "yearly_price",
        "max_operations",
        "is_active_status",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    readonly_fields = ("subscription_plan_id", "created_at", "updated_at")

    fieldsets = (
        (
            "Plan Details",
            {"fields": ("name", "description", "monthly_price", "yearly_price")},
        ),
        (
            "Features & Limits",
            {
                "fields": (
                    "max_operations",
                    "max_api_calls_per_hour",
                )
            },
        ),
        ("Feature Details", {"fields": ("feature_details",)}),
        (
            "System Fields",
            {
                "fields": (
                    "is_active",
                    "is_deleted",
                    "created_by",
                    "updated_by",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def is_active_status(self, obj):
        if obj.is_active == 1:
            return format_html('<span style="color: green;">Active</span>')
        return format_html('<span style="color: red;">Inactive</span>')

    is_active_status.short_description = "Status"


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "get_user_name",
        "get_plan_name",
        "status",
        "billing_frequency",
        "start_date",
        "end_date",
        "auto_renew",
    )
    list_filter = (
        "status",
        "billing_frequency",
        "auto_renew",
        "start_date",
        "end_date",
    )
    search_fields = ("user__full_name", "user__email", "subscription_plan__name")
    readonly_fields = ("subscription_id", "created_at", "updated_at", "last_renewed_at")
    raw_id_fields = ("user", "subscription_plan")

    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else "N/A"

    get_user_name.short_description = "User Name"

    def get_plan_name(self, obj):
        return obj.subscription_plan.name if obj.subscription_plan else "N/A"

    get_plan_name.short_description = "Plan"


@admin.register(Renewal)
class RenewalAdmin(admin.ModelAdmin):
    list_display = (
        "subscription",
        "get_user_name",
        "renewal_date",
        "renewal_cost",
        "get_renewed_by",
    )
    list_filter = ("renewal_date", "is_active")
    search_fields = ("subscription__user__full_name", "renewed_by__full_name")
    readonly_fields = ("renewal_id", "created_at", "updated_at")
    raw_id_fields = ("subscription", "renewed_by")

    def get_user_name(self, obj):
        return (
            obj.subscription.user.full_name
            if obj.subscription and obj.subscription.user
            else "N/A"
        )

    get_user_name.short_description = "User"

    def get_renewed_by(self, obj):
        return obj.renewed_by.full_name if obj.renewed_by else "System"

    get_renewed_by.short_description = "Renewed By"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "payment_id",
        "get_user_name",
        "amount",
        "payment_date",
        "payment_method",
        "status",
    )
    list_filter = ("status", "payment_method", "payment_date")
    search_fields = ("subscription__user__full_name", "reference_number")
    readonly_fields = ("payment_id", "created_at", "updated_at")
    raw_id_fields = ("subscription",)

    def get_user_name(self, obj):
        return (
            obj.subscription.user.full_name
            if obj.subscription and obj.subscription.user
            else "N/A"
        )

    get_user_name.short_description = "User"


# =============================================================================
# SYSTEM LOGS & ANALYTICS
# =============================================================================


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("activity_id", "get_user_name", "activity_type", "activity_date")
    list_filter = ("activity_type", "activity_date", "is_active")
    search_fields = ("user__full_name", "activity_type", "activity_details")
    readonly_fields = ("activity_id", "created_at", "updated_at")
    raw_id_fields = ("user",)
    date_hierarchy = "activity_date"

    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else "System"

    get_user_name.short_description = "User"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "audit_log_id",
        "get_user_name",
        "action",
        "table_affected",
        "record_id",
        "created_at",
    )
    list_filter = ("action", "table_affected", "created_at")
    search_fields = ("user__full_name", "action", "table_affected")
    readonly_fields = ("audit_log_id", "created_at", "updated_at")
    raw_id_fields = ("user",)
    date_hierarchy = "created_at"

    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else "System"

    get_user_name.short_description = "User"


@admin.register(MonthlyAnalytics)
class MonthlyAnalyticsAdmin(admin.ModelAdmin):
    list_display = (
        "analytics_id",
        "get_user_name",
        "year",
        "month",
        "renewals",
        "cancellations",
        "new_subscriptions",
        "total_payments",
    )
    list_filter = ("year", "month", "is_active")
    search_fields = ("user__full_name",)
    readonly_fields = ("analytics_id", "created_at", "updated_at")
    raw_id_fields = ("user",)

    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else "System"

    get_user_name.short_description = "User"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "notification_id",
        "get_user_name",
        "title",
        "type",
        "get_read_status",
        "created_at",
    )
    list_filter = ("type", "is_read", "is_active", "created_at")
    search_fields = ("user__full_name", "title", "message")
    readonly_fields = ("notification_id", "created_at", "updated_at")
    raw_id_fields = ("user",)

    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else "System"

    get_user_name.short_description = "User"

    def get_read_status(self, obj):
        if obj.is_read == 1:
            return format_html('<span style="color: green;">Read</span>')
        return format_html('<span style="color: orange;">● Unread</span>')

    get_read_status.short_description = "Status"


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = (
        "reminder_id",
        "get_user_name",
        "note",
        "timestamp",
        "is_active_status",
    )
    list_filter = ("timestamp", "is_active")
    search_fields = ("user__full_name", "note")
    readonly_fields = ("reminder_id", "created_at", "updated_at")
    raw_id_fields = ("user",)
    date_hierarchy = "timestamp"

    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else "System"

    get_user_name.short_description = "User"

    def is_active_status(self, obj):
        if obj.is_active == 1:
            return format_html('<span style="color: green;">Active</span>')
        return format_html('<span style="color: red;">Inactive</span>')

    is_active_status.short_description = "Status"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "event_id",
        "get_user_name",
        "title",
        "type",
        "category",
        "start_date",
        "end_date",
        "get_repeated_status",
    )
    list_filter = ("type", "category", "repeated", "frequency", "start_date")
    search_fields = ("user__full_name", "title", "description", "location")
    readonly_fields = ("event_id", "created_at", "updated_at")
    raw_id_fields = ("user",)
    date_hierarchy = "start_date"

    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else "System"

    get_user_name.short_description = "User"

    def get_repeated_status(self, obj):
        if obj.repeated == 1:
            return format_html(
                '<span style="color: blue;">{}</span>', obj.frequency or "N/A"
            )
        return format_html('<span style="color: gray;">No</span>')

    get_repeated_status.short_description = "Repeated"


# Admin site customization
admin.site.site_header = "Template Admin"
admin.site.site_title = "Template Admin"
admin.site.index_title = "Welcome to Template Administration"
