from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import F
from django.urls import reverse
from django.utils.text import slugify

TWO_PLACES = Decimal("0.01")


class Testimonial(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100, help_text="e.g. Lagos, Abuja, Port Harcourt")
    item = models.CharField(max_length=200, blank=True, help_text="What they ordered (optional)")
    message = models.TextField(help_text="Their own words, with their permission to publish")
    photo = models.ImageField(upload_to="testimonials/", blank=True)
    is_published = models.BooleanField(default=False, help_text="Tick to show on the website")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.location})"

def _unique_slug(model, value, pk=None):
    base = (slugify(value) or "item")[:100]
    slug, n = base, 2
    while model.objects.filter(slug=slug).exclude(pk=pk).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    icon = models.CharField(max_length=8, blank=True, default="🛍️", help_text="An emoji shown on category chips.")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Category, self.name, self.pk)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:category", args=[self.slug])


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(
        "original price",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    discount_percent = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(90)],
        help_text="0-90. The discounted price is calculated automatically.",
    )
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="products/", blank=True)
    image_url = models.URLField(blank=True, help_text="Optional: use an external image instead of uploading one.")
    is_active = models.BooleanField(default=True, help_text="Untick to hide the product from the store.")
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Product, self.name, self.pk)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:product_detail", args=[self.slug])

    # ---- pricing -------------------------------------------------------
    @property
    def has_discount(self):
        return self.discount_percent > 0

    @property
    def discounted_price(self):
        factor = Decimal(100 - self.discount_percent) / Decimal(100)
        return (Decimal(self.price) * factor).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    @property
    def savings(self):
        return Decimal(self.price) - self.discounted_price

    # ---- display helpers -----------------------------------------------
    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def is_low_stock(self):
        return 0 < self.stock <= settings.LOW_STOCK_THRESHOLD

    @property
    def image_src(self):
        if self.image:
            return self.image.url
        return self.image_url or ""

    @property
    def placeholder_hue(self):
        """Stable hue (0-359) used for the gradient placeholder when there is no image."""
        return ((self.pk or 0) * 47) % 360


class Order(models.Model):
    PENDING, PROCESSING, SHIPPED, DELIVERED, CANCELLED = "pending", "processing", "shipped", "delivered", "cancelled"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (PROCESSING, "Processing"),
        (SHIPPED, "Shipped"),
        (DELIVERED, "Delivered"),
        (CANCELLED, "Cancelled"),
    ]
    COD, TRANSFER = "cod", "transfer"
    PAYMENT_CHOICES = [
        (COD, "Pay on delivery"),
        (TRANSFER, "Bank transfer"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="orders"
    )
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    notes = models.TextField(blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default=COD)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.reference

    @property
    def reference(self):
        return f"TP-{self.pk:06d}" if self.pk else "TP-new"

    @property
    def status_class(self):
        return f"status-{self.status}"

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())

    @transaction.atomic
    def set_status(self, new_status):
        """Change the status. Cancelling returns the items to stock. Cancelled is final."""
        if new_status not in dict(self.STATUS_CHOICES) or new_status == self.status:
            return False
        if self.status == self.CANCELLED:
            return False
        if new_status == self.CANCELLED:
            for item in self.items.all():
                if item.product_id:
                    Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.quantity)
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])
        return True


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL, related_name="order_items")
    product_name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Discounted price at the time of purchase.")
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity
