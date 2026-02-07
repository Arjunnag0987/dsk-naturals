from django.conf import settings
from django.db import models
from django.contrib.auth.models import User


# ---------------- Product ----------------
class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="products/", null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
     
    @property
    def is_available(self):
        return self.stock > 0
     
    def save(self, *args, **kwargs):
        if self.stock < 0:
            self.stock = 0
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.name


# ---------------- Guest Customer ----------------
class GuestCustomer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField()

    def __str__(self):
        return self.name

# ---------------- Order ----------------
class Order(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders"
    )
    guest_customer = models.ForeignKey(
        GuestCustomer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    address = models.TextField()
    phone = models.CharField(max_length=15)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    payment_method = models.CharField(max_length=20, default="ONLINE")
    payment_status = models.CharField(max_length=20, default="PENDING")

    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancel_requested', 'Cancel Requested'),
        ('cancelled', 'Cancelled'),
    )

    status = models.CharField(
        max_length=40,
        choices=STATUS_CHOICES,
        default="pending"
    )

    cancel_reason = models.TextField(blank=True, null=True)
    cancelled_by = models.CharField(
        max_length=20,
        choices=(('customer', 'Customer'), ('admin', 'Admin')),
        blank=True,
        null=True
    )
    cancelled_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    delivery_otp = models.CharField(max_length=6, blank=True, null=True)
    otp_verified = models.BooleanField(default=False)
    otp_created_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Order {self.id}"


# ---------------- Order Item ----------------
class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def line_total(self):
        return self.price * self.quantity
    
# ---------------- user profile ----------------
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=15)
    profile_image = models.ImageField(
        upload_to='profiles/',
        default='profiles/default.png'
    )

    def __str__(self):
        return self.user.username
    

# ---------------- user address ----------------
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    landmark = models.CharField(max_length=100, blank=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name} - {self.city}"
    
# ----------------- Wish list ------------------
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

class HelpRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # customer message
    message = models.TextField()

    # ✅ admin reply
    admin_reply = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    replied_at = models.DateTimeField(blank=True, null=True)

    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.created_at}"    

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    landmark = models.CharField(max_length=100, blank=True)

    is_default = models.BooleanField(default=False)
    is_deliverable = models.BooleanField(default=False)  # 👈 NEW

    def __str__(self):
        return f"{self.full_name} - {self.pincode}"
    
class DeliverablePincode(models.Model):
    pincode = models.CharField(max_length=6, unique=True)
    city = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.pincode
    
class OrderTracking(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="tracking"
    )
    status = models.CharField(max_length=40)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.order.id} - {self.status}"
    
    