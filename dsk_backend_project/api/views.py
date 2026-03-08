from decimal import Decimal
import json
from pyexpat.errors import messages
import openpyxl
import razorpay
import hmac
import hashlib
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from urllib3 import request
from xhtml2pdf import pisa
import os
from django.conf import settings
from .models import DeliverablePincode, Order, OrderItem, Product, GuestCustomer ,UserProfile
from .serializers import ProductSerializer
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from .models import Wishlist
from .models import Address
from .models import UserProfile
from .models import HelpRequest, OrderTracking
from datetime import timedelta
from .utils import generate_delivery_otp, send_delivery_otp_email , generate_whatsapp_otp_link
from django.shortcuts import redirect, get_object_or_404
from urllib.parse import quote
from django.contrib import messages
from openpyxl import Workbook
from datetime import datetime
from django.db.models import Sum
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required


razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)
@csrf_exempt
def create_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=405)

    try:
        data = json.loads(request.body)
        print("🔥 ORDER DATA:", data)

        # ✅ 1. PINCODE CHECK (ADD THIS)
        pincode = data.get("pincode")

        if not pincode:
            return JsonResponse(
                {"error": "Pincode is required"},
                status=400
            )

        is_deliverable = DeliverablePincode.objects.filter(
            pincode=pincode,
            is_active=True
        ).exists()

        if not is_deliverable:
            return JsonResponse(
                {"error": "Delivery not available for this pincode"},
                status=400
            )

        # ✅ 2. CONTINUE ORDER SAFELY
        with transaction.atomic():

            # ---------------- Guest customer ----------------
            guest = None
            if not request.user.is_authenticated:
                g = data.get("guest")
                if g:
                    guest = GuestCustomer.objects.create(
                        name=g.get("name", ""),
                        phone=g.get("phone", ""),
                        email=g.get("email", ""),
                        address=g.get("address", "")
                    )

            # ---------------- Create empty order ----------------
            order = Order.objects.create(
                customer=request.user if request.user.is_authenticated else None,
                guest_customer=guest,
                address=data.get("address", ""),
                phone=data.get("phone", ""),
                subtotal=Decimal('0.00'),
                delivery_charge=Decimal('0.00'),  # temporary
                total_amount=0,
            )

            subtotal = Decimal('0.00')

            # ---------------- Order items ----------------
            for item in data.get("items", []):
                product = Product.objects.select_for_update().get(
                    id=item["product_id"]
                )

                if product.stock < item["qty"]:
                    raise Exception(f"{product.name} is out of stock")

                line_total = product.price * item["qty"]
                subtotal += line_total

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item["qty"],
                    price=product.price,
                )

                product.stock -= item["qty"]
                product.save()

            # ---------------- Update totals ----------------
            order.subtotal = subtotal
            
            if subtotal > 0 and subtotal < 1000:
                delivery_charge = Decimal('50.00')
            else:
                 delivery_charge = Decimal('0.00')
                 
            order.delivery_charge = delivery_charge
            order.total_amount = subtotal + delivery_charge    
             
            order.save()

        return JsonResponse({
            "message": "Order created successfully",
            "order_id": order.id
        }, status=201)

    except Exception as e:
        print("🔥 ORDER ERROR:", e)
        return JsonResponse({"error": str(e)}, status=400)

def product_list(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return JsonResponse(serializer.data, safe=False)
def index(request):
    products = Product.objects.filter(stock__gt=0)
    return render(request, "index.html", {"products": products})    
def cancel_order(request, order_id):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=405)

    order = get_object_or_404(Order, id=order_id)
    
    if order.customer != request.user:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    if order.status in ["delivered", "cancelled"]:
        return JsonResponse({"error": "Order cannot be cancelled"}, status=400)

    reason = request.POST.get("reason")
    if not reason:
        return JsonResponse({"error": "Cancellation reason required"}, status=400)

    order.status = "cancel_requested"
    order.cancel_reason = reason
    order.cancelled_by = "customer"
    order.cancelled_at = timezone.now()
    order.save()

    return JsonResponse({"message": "Cancellation request sent successfully"})

'''def login_view(request):
    # If already logged in, go to profile
    if request.user.is_authenticated:
      return redirect("/api/profile/")
    print("AUTH STATUS:", request.user.is_authenticated)

    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password")
        )
        if user:
            login(request, user)
            return redirect("/")

    return render(request, "login.html")'''

def login_view(request):
    # If already logged in, redirect
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Login successful")
            return redirect("/")
        else:
            return render(request, "login2.html", {
                "error": "Invalid username or password"
            })

    return render(request, "login2.html")

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        phone = request.POST.get("phone", "")

        # ✅ Prevent duplicate users
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return render(request, "register.html", {
                "error": "Username already exists"
            })

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # ✅ SAFE profile creation
        UserProfile.objects.get_or_create(
            user=user,
            defaults={"phone": phone}
        )
        messages.success(request, "Registration successful. Please log in.")
        return redirect("/login/")

    return render(request, "register.html")


def logout_view(request):
    logout(request)
    request.session.flush()  # 🔥 FORCE session clear
    messages.success(request, "Logged out successfully")    
    return redirect('/')

@login_required
def order_history(request):
    orders = Order.objects.filter(customer=request.user).order_by("-created_at")

    data = []
    for o in orders:
        data.append({
            "order_id": o.id,
            "total": o.total_amount,
            "status": o.status,
            "created_at": o.created_at.strftime("%Y-%m-%d %H:%M"),
        })

    return JsonResponse(data, safe=False)

def order_invoice(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return HttpResponse("Order not found", status=404)

    # 🔥 FIX: convert logo path to file:// URI
    logo_path = os.path.join(
        settings.BASE_DIR, "static", "images", "logo.png"
    )
    #logo_uri =  "file:///C:/Users/Arjun/OneDrive/Desktop/dsk_backend_project/static/images/logo.png"
    logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.png")
    logo_uri = f"file:///{logo_path.replace(os.sep, '/')}"


    html = render_to_string("invoice.html", {
        "order": order,
        "logo_path": logo_uri
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{order.id}.pdf"'

    result = pisa.CreatePDF(src=html, dest=response)

    if result.err:
        return HttpResponse("PDF generation failed", status=500)

    return response

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def create_razorpay_order(request):
    print("🔥 HIT create_razorpay_order")

    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=405)

    try:
        data = json.loads(request.body)
        print("🔥 REQUEST BODY:", data)

        order_id = data.get("order_id")

        if not order_id:
            return JsonResponse({"error": "order_id missing"}, status=400)

        order = Order.objects.get(id=order_id)
        print("🔥 ORDER FOUND:", order.id)

        # 🔥 IMPORTANT
        amount = int(order.total * 100)

        razorpay_order = razorpay_client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1
        })

        print("🔥 RAZORPAY ORDER:", razorpay_order)

        order.razorpay_order_id = razorpay_order["id"]
        order.save()

        return JsonResponse({
            "key": settings.RAZORPAY_KEY_ID,
            "amount": amount,
            "razorpay_order_id": razorpay_order["id"]
        })

    except Order.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)

    except Exception as e:
        print("🔥 BACKEND ERROR:", e)
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def verify_payment(request):
    data = json.loads(request.body)

    try:
        order = Order.objects.get(
            razorpay_order_id=data["razorpay_order_id"]
        )
    except Order.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)

    generated_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{data['razorpay_order_id']}|{data['razorpay_payment_id']}".encode(),
        hashlib.sha256
    ).hexdigest()

    if generated_signature == data["razorpay_signature"]:
        order.payment_status = "PAID"
        order.status = "confirmed"
        order.razorpay_payment_id = data["razorpay_payment_id"]
        order.razorpay_signature = data["razorpay_signature"]
        order.save()
        return JsonResponse({
            "status": "success",
            "order_id": order.id})

    order.payment_status = "FAILED"
    order.save()
    return JsonResponse({"status": "failed"}, status=400)

def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    return JsonResponse({
        "order_id": order.id,
        "total": order.total_amount,
        "status": order.status,
        "created_at": order.created_at.strftime("%Y-%m-%d %H:%M"),
    })    

@login_required
def my_orders(request):
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    for order in orders:
        order.whatsapp_link = generate_whatsapp_otp_link(order)
    return render(request, 'profile/orders.html', {'orders': orders})

@login_required
def wishlist_view(request):
    items = Wishlist.objects.filter(user=request.user)
    return render(request, 'profile/wishlist.html', {'items': items})


@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    obj, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        obj.delete()
        return JsonResponse({"status": "removed"})

    return JsonResponse({"status": "added"})

@login_required
def address_list(request):
    edit_address = None

    # Check if editing
    address_id = request.GET.get("edit")
    if address_id:
        edit_address = get_object_or_404(
            Address, id=address_id, user=request.user
        )

    if request.method == "POST":
        if request.POST.get("address_id"):
            # ✏️ Update address
            addr = get_object_or_404(
                Address,
                id=request.POST.get("address_id"),
                user=request.user
            )
        else:
            # ➕ New address
            addr = Address(user=request.user)

        addr.full_name = request.POST.get("full_name")
        addr.phone = request.POST.get("phone")
        addr.address = request.POST.get("address")
        addr.city = request.POST.get("city")
        addr.state = request.POST.get("state")
        addr.pincode = request.POST.get("pincode")
        addr.save()

        return redirect("/api/address/")

    addresses = Address.objects.filter(user=request.user)

    return render(request, "profile/address.html", {
        "addresses": addresses,
        "edit_address": edit_address
    })
 

@login_required
def profile_dashboard(request):
    profile, created = UserProfile.objects.get_or_create(
        user=request.user
    )
    return render(request, "profile/profile.html", {
        "profile": profile
    })  
    
@login_required
def edit_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # ✅ Update USER model
        name = request.POST.get("name")
        phone = request.POST.get("phone")

        if name:
            request.user.username = name
            request.user.save()

        # ✅ Update PROFILE model
        profile.phone = phone

        if "profile_image" in request.FILES:
            profile.profile_image = request.FILES["profile_image"]

        profile.save()

        return redirect("/api/profile/")

    return render(request, "profile/edit_profile.html", {
        "profile": profile
    })
 
    
@login_required
def help_center(request):

    if request.method == "POST":
        message = request.POST.get("message")

        if message:
            HelpRequest.objects.create(
                user=request.user,
                message=message
            )

    help_requests = HelpRequest.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(request, "profile/help.html", {
        "help_requests": help_requests
    })


@login_required
def upload_profile_image(request):
    if request.method == "POST" and request.FILES.get("profile_image"):
        profile = request.user.profile
        profile.profile_image = request.FILES["profile_image"]
        profile.save()

    return redirect("/api/profile/")

@login_required
def delete_address(request, address_id):
    if request.method == "POST":
        address = get_object_or_404(
            Address,
            id=address_id,
            user=request.user
        )
        address.delete()

    return redirect("/api/address/")

@login_required
def address_list(request):
    edit_address = None

    address_id = request.GET.get("edit")
    if address_id:
        edit_address = get_object_or_404(
            Address, id=address_id, user=request.user
        )

    if request.method == "POST":
        if request.POST.get("address_id"):
            addr = get_object_or_404(
                Address,
                id=request.POST.get("address_id"),
                user=request.user
            )
        else:
            addr = Address(user=request.user)

        addr.full_name = request.POST.get("full_name")
        addr.phone = request.POST.get("phone")
        addr.address = request.POST.get("address")
        addr.city = request.POST.get("city")
        addr.state = request.POST.get("state")
        addr.pincode = request.POST.get("pincode")

        # ✅ DELIVERY CHECK
        addr.is_deliverable = DeliverablePincode.objects.filter(
            pincode=addr.pincode,
            is_active=True
        ).exists()

        addr.save()
        return redirect("/api/address/")

    addresses = Address.objects.filter(user=request.user)

    return render(request, "profile/address.html", {
        "addresses": addresses,
        "edit_address": edit_address
    })

def check_pincode(request):
    data = json.loads(request.body)
    pincode = data.get("pincode")

    exists = DeliverablePincode.objects.filter(
        pincode=pincode,
        is_active=True
    ).exists()

    return JsonResponse({"deliverable": exists})    

def mark_out_for_delivery(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status != "confirmed":
        return JsonResponse({"error": "Order not ready"}, status=400)

    # 🔐 Generate OTP
    otp = generate_delivery_otp()
    order.delivery_otp = otp
    order.otp_created_at = timezone.now()
    order.status = "out_for_delivery"
    order.save()

    # 📦 Tracking entry
    OrderTracking.objects.create(
        order=order,
        status="out_for_delivery",
        message="Order is out for delivery"
    )

    # 📧 SEND EMAIL OTP
    send_delivery_otp_email(order)

    return JsonResponse({
        "message": "Order marked Out for Delivery & OTP sent"
    })
    
def delivery_agent_verify_otp(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    error = None
    success = None

    if order.status == "delivered":
        success = "Order already delivered"
        return render(request, "delivery_verify.html", {"success": success})

    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        if not order.delivery_otp:
            error = "OTP not generated yet"

        elif entered_otp == order.delivery_otp:
            order.status = "delivered"
            order.delivery_otp = None
            order.save()

            OrderTracking.objects.create(
                order=order,
                status="delivered",
                message="Order delivered successfully"
            )

            success = "✅ Delivery completed successfully"

        else:
            error = "❌ Invalid OTP"

    return render(
        request,
        "delivery_verify.html",
        {
            "order": order,
            "error": error,
            "success": success,
        }
    )

def delivery_agent_whatsapp(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status != "out_for_delivery":
        return JsonResponse({"error": "Order not out for delivery"}, status=400)

    if not order.delivery_otp:
        return JsonResponse({"error": "OTP not generated"}, status=400)

    # clean phone
    phone = order.phone.replace("+", "").replace(" ", "")
    if phone.startswith("91"):
        phone = phone[2:]

    message = (
        "Hello\n\n"
        "DSK Naturals Delivery\n\n"
        f"Order ID: #{order.id}\n"
        f"Delivery OTP: {order.delivery_otp}\n\n"
        "Please share this OTP to confirm delivery.\n\n"
        "Thank you,\nDSK Naturals"
    )

    encoded_message = quote(message)

    whatsapp_url = (
        f"https://api.whatsapp.com/send"
        f"?phone=91{phone}&text={encoded_message}"
    )

    return redirect(whatsapp_url)

@staff_member_required
def admin_dashboard(request):

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    orders = Order.objects.filter(payment_status="PAID")

    if start_date and end_date:
        orders = orders.filter(
            created_at__date__range=[start_date, end_date]
        )

    total_orders = orders.count()
    total_revenue = orders.aggregate(
        Sum("total_amount")
    )["total_amount__sum"] or 0

    # 📊 Chart Data (Last 7 days)
    last_7_days = []
    revenue_data = []

    for i in range(6, -1, -1):
        day = timezone.now().date() - timezone.timedelta(days=i)
        daily_total = Order.objects.filter(
            payment_status="PAID",
            created_at__date=day
        ).aggregate(Sum("total_amount"))["total_amount__sum"] or 0

        last_7_days.append(day.strftime("%d %b"))
        revenue_data.append(float(daily_total))

    context = {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "labels": last_7_days,
        "data": revenue_data,
    }

    return render(request, "admin_dashboard.html", context) 

@staff_member_required
def export_sales_excel(request):

    orders = Order.objects.filter(payment_status="PAID")

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sales Report"

    sheet.append(["Order ID", "Customer", "Total Amount", "Date"])

    for order in orders:
        sheet.append([
            order.id,
            order.customer.username if order.customer else "Guest",
            float(order.total_amount),
            order.created_at.strftime("%Y-%m-%d"),
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="sales_report.xlsx"'

    workbook.save(response)
    return response