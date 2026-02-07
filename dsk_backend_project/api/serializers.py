# api/serializers.py

from rest_framework import serializers
from decimal import Decimal, InvalidOperation
from django.db import IntegrityError, transaction

from .models import Product, Order


class ProductSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields =  [
            "id",
            "name",
            "stock",
            "description",
            "price",
            "image",
            "is_available",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "is_available"]
    def get_is_available(self, obj):
        return obj.stock > 0

class OrderSerializer(serializers.ModelSerializer):
    # Customer is stored as JSON in the model, so expose it as JSONField (read-only)
    customer = serializers.JSONField(read_only=True)
    items = serializers.JSONField()

    class Meta:
        model = Order
        # only include fields that actually exist on your model
        fields = [
            "id", "customer", "items", "subtotal",
            "delivery_charge", "total_amount", "status", "created_at"
        ]
        read_only_fields = ["id", "status", "created_at", "subtotal", "delivery_charge", "total_amount"]

    def create(self, validated_data):
        items = validated_data.pop("items", []) or []

        # compute subtotal with Decimal
        subtotal = Decimal("0.00")
        for it in items:
            price = it.get("price") or it.get("unit_price") or 0
            qty = it.get("qty") or it.get("quantity") or 1
            try:
                subtotal += Decimal(str(price)) * Decimal(int(qty))
            except (InvalidOperation, TypeError, ValueError):
                continue

        delivery = Decimal("30.00") if Decimal("0.00") < subtotal < Decimal("500.00") else Decimal("0.00")
        total_amount = subtotal + delivery

        validated_data["subtotal"] = subtotal
        validated_data["delivery_charge"] = delivery
        validated_data["total_amount"] = total_amount

        # attach customer as a JSON dict (so it's storable in your JSONField)
        request = self.context.get("request") if self.context else None
        if request and hasattr(request, "user") and request.user.is_authenticated:
            user = request.user
            # store minimal user info as JSON (customize as needed)
            validated_data["customer"] = {
                "id": user.id,
                "username": getattr(user, "username", None),
                "email": getattr(user, "email", None),
                "name": getattr(user, "get_full_name", lambda: None)() or getattr(user, "username", None),
            }
        else:
            # if anonymous orders allowed, keep customer as empty dict or require frontend to send it
            validated_data["customer"] = validated_data.get("customer", {})

        validated_data["items"] = items

        try:
            with transaction.atomic():
                return super().create(validated_data)
        except IntegrityError as e:
            raise serializers.ValidationError({"error": f"Database error: {e}"})
        except Exception as e:
            raise serializers.ValidationError({"error": f"Unexpected error: {e}"})