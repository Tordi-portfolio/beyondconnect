from django.contrib import admin, messages

from .models import Category, Order, OrderItem, Product, Testimonial


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "item", "is_published", "created_at")
    list_editable = ("is_published",)
    list_filter = ("is_published",)
    search_fields = ("name", "location", "message")

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "category", "price", "discount_percent", "discounted_price_display", "stock", "is_active", "is_featured",
    )
    list_editable = ("discount_percent", "stock", "is_active", "is_featured")
    list_filter = ("category", "is_active", "is_featured")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_per_page = 25
    actions = ["remove_discount", "discount_10", "discount_20", "mark_featured"]

    @admin.display(description="Sale price")
    def discounted_price_display(self, obj):
        return obj.discounted_price

    @admin.action(description="Remove discount from selected products")
    def remove_discount(self, request, queryset):
        self.message_user(request, f"Discount removed from {queryset.update(discount_percent=0)} product(s).")

    @admin.action(description="Set 10 percent discount on selected products")
    def discount_10(self, request, queryset):
        self.message_user(request, f"10% discount set on {queryset.update(discount_percent=10)} product(s).")

    @admin.action(description="Set 20 percent discount on selected products")
    def discount_20(self, request, queryset):
        self.message_user(request, f"20% discount set on {queryset.update(discount_percent=20)} product(s).")

    @admin.action(description="Mark selected products as featured")
    def mark_featured(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_featured=True)} product(s) featured.", messages.SUCCESS)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "unit_price", "quantity")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "full_name", "total", "payment_method", "status", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("full_name", "email", "phone", "user__username")
    date_hierarchy = "created_at"
    readonly_fields = ("user", "subtotal", "shipping_fee", "total", "created_at", "updated_at")
    inlines = [OrderItemInline]
