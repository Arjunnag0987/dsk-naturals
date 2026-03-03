# api/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import UserProfile, Order
from .utils import send_delivery_otp_email, send_delivery_sms


# 🔹 Create profile automatically
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


# 🔹 Handle Order Status Change
@receiver(post_save, sender=Order)
def order_status_handler(sender, instance, created, **kwargs):

    # Only when status becomes out_for_delivery
    if instance.status == "out_for_delivery" and not instance.delivery_otp:

        # Generate OTP
        instance.generate_delivery_otp()

        # Send OTP Email
        send_delivery_otp_email(instance)

        # Send OTP SMS
        send_delivery_sms(instance)
