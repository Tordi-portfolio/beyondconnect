from decimal import Decimal

from django.conf import settings

from .cart import Cart
from .models import Category


def site(request):
    """Values available in every template."""
    return {
        "SITE_NAME": settings.SITE_NAME,
        "CURRENCY": settings.CURRENCY_SYMBOL,
        "FREE_SHIPPING": Decimal(str(settings.FREE_SHIPPING_THRESHOLD)),
        "cart_count": len(Cart(request)),
        "nav_categories": Category.objects.all()[:8],
    }
