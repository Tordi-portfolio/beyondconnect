from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.models import Profile

from .cart import Cart
from .forms import CheckoutForm, TestimonialForm
from .models import Category, Order, OrderItem, Product, Testimonial
from .whatsapp import build_whatsapp_url

PAGE_SIZE = 12

SORT_OPTIONS = [
    ("relevance", "Most relevant"),
    ("newest", "Newest"),
    ("price_low", "Price: low to high"),
    ("price_high", "Price: high to low"),
    ("discount", "Biggest discount"),
    ("name", "Name: A to Z"),
]


from datetime import timedelta

from django.contrib.auth.views import redirect_to_login
from django.utils import timezone

class StockError(Exception):
    pass


def testimonials(request):
    initial = {}
    if request.user.is_authenticated:
        initial["name"] = request.user.get_full_name() or request.user.username
    form = TestimonialForm(request.POST or None, initial=initial)

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        recent = Testimonial.objects.filter(
            user=request.user, created_at__gte=timezone.now() - timedelta(days=1)
        ).count()
        if recent >= 3:
            messages.error(request, "You've reached today's limit for testimonies. Please try again tomorrow.")
            return redirect("store:testimonials")

        if form.is_valid():
            testimony = form.save(commit=False)
            testimony.user = request.user
            testimony.is_published = False  # you approve it in the admin first
            testimony.save()
            messages.success(request, "Thank you! Your testimony has been received and will appear once we approve it.")
            return redirect("store:testimonials")

    return render(request, "store/testimonials.html", {
        "testimonials": Testimonial.objects.filter(is_published=True),
        "form": form,
    })

def about(request):
    return render(request, "store/about.html")

def contact(request):
    return render(request, "store/contact.html")

def _safe_redirect(request, default, *args):
    target = request.POST.get("next") or request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(target)
    return redirect(default, *args)


# --------------------------------------------------------------------------
# Browsing & search
# --------------------------------------------------------------------------
def home(request):
    active = Product.objects.filter(is_active=True).select_related("category")
    context = {
        "categories": Category.objects.annotate(
            product_total=Count("products", filter=Q(products__is_active=True))
        ),
        "deals": active.filter(discount_percent__gt=0, stock__gt=0).order_by("-discount_percent")[:8],
        "featured": active.filter(is_featured=True)[:8],
        "newest": active.order_by("-created_at")[:4],
    }
    return render(request, "store/home.html", context)


def product_list(request, category_slug=None):
    """Product listing. Also powers search (?q=), sorting and the 'on sale' filter."""
    query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "relevance")
    deals_only = request.GET.get("deals") == "1"
    category = get_object_or_404(Category, slug=category_slug) if category_slug else None

    products = Product.objects.filter(is_active=True).select_related("category")
    if category:
        products = products.filter(category=category)
    if deals_only:
        products = products.filter(discount_percent__gt=0)
    if query:
        # Every word must match the name, description or category name.
        for term in query.split()[:6]:
            products = products.filter(
                Q(name__icontains=term) | Q(description__icontains=term) | Q(category__name__icontains=term)
            )

    # Sorting (net_price = price after discount, scaled by 100 which is fine for ordering).
    products = products.annotate(
        net_price=ExpressionWrapper(
            F("price") * (100 - F("discount_percent")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )
    if sort == "price_low":
        products = products.order_by("net_price", "name")
    elif sort == "price_high":
        products = products.order_by("-net_price", "name")
    elif sort == "discount":
        products = products.order_by("-discount_percent", "name")
    elif sort == "name":
        products = products.order_by("name")
    elif sort == "newest":
        products = products.order_by("-created_at")
    else:
        sort = "relevance"
        if query:
            products = products.annotate(
                rel=Case(
                    When(name__icontains=query, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            ).order_by("rel", "-is_featured", "-created_at")
        else:
            products = products.order_by("-is_featured", "-created_at")

    paginator = Paginator(products, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page,
        "products": page.object_list,
        "result_count": paginator.count,
        "query": query,
        "category": category,
        "sort": sort,
        "sort_options": SORT_OPTIONS,
        "deals_only": deals_only,
        "categories": Category.objects.all(),
    }
    return render(request, "store/product_list.html", context)


def search_suggestions(request):
    """Small JSON endpoint powering the search-as-you-type dropdown."""
    query = request.GET.get("q", "").strip()
    results = []
    if len(query) >= 2:
        matches = (
            Product.objects.filter(is_active=True)
            .filter(Q(name__icontains=query) | Q(category__name__icontains=query))
            .order_by("name")[:6]
        )
        results = [
            {
                "name": p.name,
                "url": p.get_absolute_url(),
                "price": f"{settings.CURRENCY_SYMBOL}{p.discounted_price:,.2f}",
            }
            for p in matches
        ]
    return JsonResponse({"results": results})


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related("category"), slug=slug, is_active=True)
    related = (
        Product.objects.filter(is_active=True, category=product.category)
        .exclude(pk=product.pk)
        .select_related("category")[:4]
    )
    max_qty = min(product.stock, 10)
    context = {"product": product, "related": related, "quantities": range(1, max_qty + 1)}
    return render(request, "store/product_detail.html", context)


# --------------------------------------------------------------------------
# Cart
# --------------------------------------------------------------------------
def cart_detail(request):
    return render(request, "store/cart.html", {"cart": Cart(request)})


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    try:
        quantity = max(1, int(request.POST.get("quantity", 1)))
    except ValueError:
        quantity = 1

    if not product.in_stock:
        messages.error(request, f"Sorry, {product.name} is out of stock.")
        return _safe_redirect(request, "store:product_detail", product.slug)

    cart = Cart(request)
    final = cart.add(product, quantity)
    messages.success(request, f"Added to your cart: {product.name} (now {final} in cart).")
    if request.POST.get("buy_now") == "1":
        return redirect("store:cart")
    return _safe_redirect(request, "store:cart")


@require_POST
def update_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    try:
        quantity = int(request.POST.get("quantity", 1))
    except ValueError:
        quantity = 1
    cart = Cart(request)
    final = cart.add(product, quantity, override=True)
    if final < quantity:
        messages.warning(request, f"Only {final} of {product.name} can be ordered right now.")
    return redirect("store:cart")


@require_POST
def remove_from_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    Cart(request).remove(product)
    messages.info(request, f"Removed {product.name} from your cart.")
    return redirect("store:cart")


# --------------------------------------------------------------------------
# Checkout
# --------------------------------------------------------------------------
@login_required
def checkout(request):
    cart = Cart(request)
    if not cart.lines:
        messages.info(request, "Your cart is empty.")
        return redirect("store:cart")

    profile = Profile.for_user(request.user)
    initial = {
        "full_name": request.user.get_full_name(),
        "email": request.user.email,
        "phone": profile.phone,
        "address": profile.address,
        "city": profile.city,
    }
    form = CheckoutForm(request.POST or None, initial=initial)

    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                lines = cart.lines
                locked = {
                    p.pk: p
                    for p in Product.objects.select_for_update().filter(pk__in=[l["product"].pk for l in lines])
                }
                for line in lines:
                    product = locked[line["product"].pk]
                    if line["quantity"] > product.stock:
                        raise StockError(f"Only {product.stock} of {product.name} left in stock.")

                order = form.save(commit=False)
                order.user = request.user
                order.subtotal = cart.subtotal
                order.shipping_fee = cart.shipping
                order.total = cart.total
                order.save()

                for line in lines:
                    product = locked[line["product"].pk]
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        unit_price=line["unit_price"],
                        quantity=line["quantity"],
                    )
                    product.stock -= line["quantity"]
                    product.save(update_fields=["stock", "updated_at"])
        except StockError as exc:
            messages.error(request, f"{exc} Please adjust your cart.")
            return redirect("store:cart")

        # Remember contact details for next time if the profile is empty.
        changed = False
        for field in ("phone", "address", "city"):
            if not getattr(profile, field) and form.cleaned_data.get(field):
                setattr(profile, field, form.cleaned_data[field])
                changed = True
        if changed:
            profile.save()

        cart.clear()
        request.session["whatsapp_redirect_order"] = order.pk  # auto-open WhatsApp once, on the thank-you page
        messages.success(request, f"Thank you! Your order {order.reference} has been placed.")
        return redirect("store:order_success", pk=order.pk)

    return render(request, "store/checkout.html", {"cart": cart, "form": form})


@login_required
def order_success(request, pk):
    order = get_object_or_404(request.user.orders.prefetch_related("items"), pk=pk)
    # Only auto-redirect right after checkout, not when the page is revisited later.
    auto_redirect = request.session.pop("whatsapp_redirect_order", None) == order.pk
    context = {
        "order": order,
        "whatsapp_url": build_whatsapp_url(order),
        "auto_redirect": auto_redirect,
    }
    return render(request, "store/order_success.html", context)


# --------------------------------------------------------------------------
# Error pages
# --------------------------------------------------------------------------
def permission_denied(request, exception=None):
    return render(request, "403.html", status=403)


def page_not_found(request, exception=None):
    return render(request, "404.html", status=404)
