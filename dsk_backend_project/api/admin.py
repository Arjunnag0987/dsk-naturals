from django.contrib import admin
from .models import HelpRequest, Product, Order, OrderItem, GuestCustomer ,Address , DeliverablePincode,OrderTracking
from django.utils import timezone
from .utils import generate_delivery_otp, send_delivery_otp_email

# ---------- Product ----------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "price",
        "stock",          # ✅ real field
        "is_available",   # ✅ property (display only)
        "created_at",
    )

    list_editable = (
        "stock",          # ✅ real field ONLY
    )

    list_filter = (
        "created_at",     # ✅ real field ONLY
    )

    search_fields = ("name",)


# ---------- Order Items Inline ----------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "price")

class OrderTrackingInline(admin.TabularInline):
    model = OrderTracking
    extra = 0
    readonly_fields = ("status", "message", "created_at")
    can_delete = False

# ---------- Order ----------
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "phone",
        "total_amount",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    # ❌ DO NOT put stock or is_available here
    # ❌ list_editable REMOVED

    inlines = [OrderItemInline,
               OrderTrackingInline,]

    readonly_fields = ("created_at",)
    
    def save_model(self, request, obj, form, change):
        if change:
            old_obj = Order.objects.get(pk=obj.pk)

            if old_obj.status != obj.status:
                OrderTracking.objects.create(
                    order=obj,
                    status=obj.status,
                    message=f"Order status updated to {obj.get_status_display()}"
                )
                if obj.status == "out_for_delivery":
                    obj.delivery_otp = generate_delivery_otp()
                    obj.otp_verified = False
                    obj.otp_created_at = timezone.now()
                    obj.save(update_fields=["delivery_otp", "otp_verified"])

                    # ✅ THIS CALL REMOVES THE WARNING
                    send_delivery_otp_email(obj)

        super().save_model(request, obj, form, change)


# ---------- Guest Customer ----------
@admin.register(GuestCustomer)
class GuestCustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email")
    search_fields = ("name", "phone")

# ---------- help center ----------    
@admin.register(HelpRequest)
class HelpRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "short_message",
        "is_resolved",
        "created_at",
    )

    list_filter = ("is_resolved", "created_at")
    search_fields = ("user__username", "message")
    list_editable = ("is_resolved",)

    readonly_fields = ("user", "message", "created_at", "replied_at")

    fields = (
        "user",
        "message",
        "admin_reply",     # ✅ admin can type reply
        "is_resolved",
        "created_at",
        "replied_at",
    )

    def short_message(self, obj):
        return obj.message[:50]

    # ✅ auto set reply time
    def save_model(self, request, obj, form, change):
        if obj.admin_reply and not obj.replied_at:
            obj.replied_at = timezone.now()
        super().save_model(request, obj, form, change)
   
    
@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "full_name",
        "phone",
        "city",
        "state",
        "pincode",
        "is_default",
    )

    list_filter = (
        "city",
        "state",
        "is_default",
    )

    search_fields = (
        "user__username",
        "full_name",
        "phone",
        "city",
        "pincode",
    )

    list_editable = ("is_default",)

@admin.register(DeliverablePincode)
class DeliverablePincodeAdmin(admin.ModelAdmin):
    list_display = ("pincode", "city", "is_active")
    list_editable = ("is_active",)
    search_fields = ("pincode", "city")

   