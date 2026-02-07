import random
from django.core.mail import send_mail
import urllib.parse
from django.conf import settings


def generate_delivery_otp():
    return str(random.randint(100000, 999999))


def get_order_email(order):
    if order.guest_customer and order.guest_customer.email:
        return order.guest_customer.email
    if order.customer and order.customer.email:
        return order.customer.email
    return None


def send_delivery_otp_email(order):
    email = get_order_email(order)
    if not email:
        return

    send_mail(
        subject="DSK Naturals – Delivery OTP",
        message=(
            f"Dear Customer,\n\n"
            f"Your order #{order.id} is out for delivery 🚚\n\n"
            f"Delivery OTP: {order.delivery_otp}\n\n"
            f"Please share this OTP with the delivery agent.\n\n"
            f"Thank you,\nDSK Naturals"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


def generate_whatsapp_otp_link(order):
    phone = None

    # decide phone number
    if order.guest_customer and order.guest_customer.phone:
        phone = order.guest_customer.phone
    elif order.customer and hasattr(order.customer, "profile"):
        phone = order.customer.profile.phone

    if not phone:
        return None

    # ensure Indian format (91XXXXXXXXXX)
    phone = phone.replace("+", "").replace(" ", "")
    if not phone.startswith("91"):
        phone = "91" + phone

    message = (
        "🌿 DSK Naturals\n\n"
        f"Your order #{order.id} is out for delivery 🚚\n"
        f"🔐 Delivery OTP: {order.delivery_otp}\n\n"
        "Please share this OTP with the delivery agent.\n\n"
        "🌱 Where Purity Meets Flavour"
    )

    encoded_message = urllib.parse.quote(message)

    return f"https://wa.me/{phone}?text={encoded_message}"