from decimal import Decimal

from django.conf import settings

from .models import Product


class Cart:
    """A session-backed shopping cart: {product_id: quantity}."""

    SESSION_KEY = "cart"

    def __init__(self, request):
        self.session = request.session
        self.items = dict(self.session.get(self.SESSION_KEY, {}))
        self._lines = None

    # ---- mutation ------------------------------------------------------
    def _save(self):
        self.session[self.SESSION_KEY] = self.items
        self.session.modified = True
        self._lines = None

    def add(self, product, quantity=1, override=False):
        """Add (or set) a quantity, clamped to stock and the per-item maximum. Returns the final quantity."""
        key = str(product.pk)
        wanted = quantity if override else self.items.get(key, 0) + quantity
        final = max(0, min(wanted, product.stock, settings.MAX_CART_QUANTITY))
        if final == 0:
            self.items.pop(key, None)
        else:
            self.items[key] = final
        self._save()
        return final

    def remove(self, product):
        self.items.pop(str(product.pk), None)
        self._save()

    def clear(self):
        self.items = {}
        self.session.pop(self.SESSION_KEY, None)
        self.session.modified = True
        self._lines = None

    # ---- reading -------------------------------------------------------
    @property
    def lines(self):
        if self._lines is None:
            ids = [int(pk) for pk in self.items]
            products = {
                p.pk: p for p in Product.objects.filter(pk__in=ids, is_active=True).select_related("category")
            }
            lines = []
            for pk, quantity in self.items.items():
                product = products.get(int(pk))
                if product is None:
                    continue
                price = product.discounted_price
                lines.append(
                    {"product": product, "quantity": quantity, "unit_price": price, "line_total": price * quantity}
                )
            self._lines = lines
        return self._lines

    def __len__(self):
        return sum(self.items.values())

    @property
    def subtotal(self):
        return sum((line["line_total"] for line in self.lines), Decimal("0.00"))

    @property
    def shipping(self):
        subtotal = self.subtotal
        if subtotal == 0 or subtotal >= Decimal(str(settings.FREE_SHIPPING_THRESHOLD)):
            return Decimal("0.00")
        return Decimal(str(settings.SHIPPING_FEE))

    @property
    def total(self):
        return self.subtotal + self.shipping

    @property
    def amount_to_free_shipping(self):
        remaining = Decimal(str(settings.FREE_SHIPPING_THRESHOLD)) - self.subtotal
        return remaining if remaining > 0 else Decimal("0.00")

    @property
    def free_shipping_progress(self):
        """Percentage (0-100) of the way to free delivery."""
        threshold = Decimal(str(settings.FREE_SHIPPING_THRESHOLD))
        if threshold <= 0:
            return 100
        return min(100, int(self.subtotal * 100 / threshold))
