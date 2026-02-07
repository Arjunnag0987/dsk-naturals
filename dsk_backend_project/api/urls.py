from django.urls import path
from . import views   
from .views import (
    cancel_order,
    create_order,
    create_razorpay_order,
    edit_profile,
    help_center,
    product_list,
    upload_profile_image,
    verify_payment,
    order_history,
    order_invoice,
    login_view,
    register_view,
    logout_view,
    my_orders,          
    wishlist_view,      
    address_list,       
    profile_dashboard,
)
urlpatterns = [
    # ---------------- Orders & Payments ----------------
    path("orders/create/", views.create_order, name="create_order"),
    path("create-razorpay-order/", views.create_razorpay_order, name="create_razorpay_order"),
    path("verify-payment/", views.verify_payment, name="verify_payment"),
    path("order-history/", views.order_history, name="order_history"),
    path("invoice/<int:order_id>/", views.order_invoice, name="order_invoice"),
    path("order/<int:order_id>/cancel/", views.cancel_order, name="cancel_order"),

    # ---------------- Products ----------------
    path("products/", product_list, name="product_list"),

    

    # ---------------- Profile Section ----------------
    path("profile/", views.profile_dashboard, name="profile"),
    path("orders/", views.my_orders, name="my_orders"),
    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("address/", views.address_list, name="address"),
    path("edit/", views.edit_profile, name="edit_profile"),
    path("help/", views.help_center, name="help"),
    path("profile/upload-image/", upload_profile_image, name="upload_profile_image"),
    path("address/delete/<int:address_id>/",views.delete_address,name="delete_address"),
    path("delivery/verify/<int:order_id>/",views.delivery_agent_verify_otp,name="delivery_verify"),
    path("delivery/whatsapp/<int:order_id>/",views.delivery_agent_whatsapp,name="delivery_whatsapp"),


]
