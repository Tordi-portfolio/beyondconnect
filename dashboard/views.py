from datetime import timedelta
from decimal import Decimal
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from store.models import Category, Order, OrderItem, Product

User = get_user_model()

# Statuses that count towards revenue / customer spend (everything except cancelled).
COUNTED_STATUSES = [key for key, _ in Order.STATUS_CHOICES if key != Order.CANCELLED]


def staff_required(view_func):
    """Only logged-in staff may enter. Anonymous users go to login; customers get a 403."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper


@staff_required
def home(request):
    today = timezone.localdate()
    week_start = today - timedelta(days=6)
    valid_orders = Order.objects.exclude(status=Order.CANCELLED)

    revenue = valid_orders.aggregate(t=Sum("total"))["t"] or Decimal("0.00")
    revenue_today = valid_orders.filter(created_at__date=today).aggregate(t=Sum("total"))["t"] or Decimal("0.00")
    order_total = Order.objects.count()
    pending = Order.objects.filter(status=Order.PENDING).count()
    customers = User.objects.filter(is_staff=False).count()
    new_customers = User.objects.filter(is_staff=False, date_joined__date__gte=week_start).count()
    avg_order = (revenue / valid_orders.count()) if valid_orders.exists() else Decimal("0.00")

    # Sales for the last 7 days (fill gaps with zero so the chart always has 7 bars).
    daily = {
        row["day"]: row
        for row in valid_orders.filter(created_at__date__gte=week_start)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Sum("total"), n=Count("id"))
    }
    days = []
    for offset in range(7):
        day = week_start + timedelta(days=offset)
        row = daily.get(day)
        days.append({"day": day, "total": row["total"] if row else Decimal("0.00"), "orders": row["n"] if row else 0})
    peak = max((d["total"] for d in days), default=Decimal("0.00"))
    for d in days:
        d["pct"] = int((d["total"] / peak) * 100) if peak else 0

    status_counts = {row["status"]: row["n"] for row in Order.objects.values("status").annotate(n=Count("id"))}
    statuses = [
        {"key": key, "label": label, "count": status_counts.get(key, 0),
         "pct": int(status_counts.get(key, 0) * 100 / order_total) if order_total else 0}
        for key, label in Order.STATUS_CHOICES
    ]

    top_products = (
        OrderItem.objects.exclude(order__status=Order.CANCELLED)
        .values("product_name")
        .annotate(
            units=Sum("quantity"),
            revenue=Sum(
                ExpressionWrapper(
                    F("unit_price") * F("quantity"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ),
        )
        .order_by("-units")[:5]
    )

    context = {
        "revenue": revenue,
        "revenue_today": revenue_today,
        "order_total": order_total,
        "pending": pending,
        "customers": customers,
        "new_customers": new_customers,
        "avg_order": avg_order,
        "product_total": Product.objects.count(),
        "active_products": Product.objects.filter(is_active=True).count(),
        "days": days,
        "week_total": sum((d["total"] for d in days), Decimal("0.00")),
        "statuses": statuses,
        "top_products": top_products,
        "recent_orders": Order.objects.select_related("user")[:8],
        "recent_users": User.objects.order_by("-date_joined")[:6],
        "low_stock": Product.objects.filter(is_active=True, stock__lte=settings.LOW_STOCK_THRESHOLD)
        .select_related("category")
        .order_by("stock")[:8],
        "section": "overview",
    }
    return render(request, "dashboard/home.html", context)


@staff_required
def orders(request):
    status = request.GET.get("status", "")
    query = request.GET.get("q", "").strip()
    qs = Order.objects.select_related("user").prefetch_related("items")
    if status in dict(Order.STATUS_CHOICES):
        qs = qs.filter(status=status)
    if query:
        cond = Q(full_name__icontains=query) | Q(email__icontains=query) | Q(user__username__icontains=query)
        digits = query.upper().replace("TP-", "").lstrip("0")
        if digits.isdigit():
            cond |= Q(pk=int(digits))
        qs = qs.filter(cond)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    context = {
        "page_obj": page,
        "status": status,
        "query": query,
        "status_choices": Order.STATUS_CHOICES,
        "section": "orders",
    }
    return render(request, "dashboard/orders.html", context)


@staff_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related("user").prefetch_related("items"), pk=pk)
    return render(
        request,
        "dashboard/order_detail.html",
        {"order": order, "status_choices": Order.STATUS_CHOICES, "section": "orders"},
    )


@staff_required
@require_POST
def update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    new_status = request.POST.get("status", "")
    if order.set_status(new_status):
        messages.success(request, f"{order.reference} is now {order.get_status_display().lower()}.")
    else:
        messages.error(request, "That status change isn't allowed (cancelled orders can't be reopened).")
    # The status dropdown on the orders list sends return_to=list; the detail page doesn't.
    if request.POST.get("return_to") == "list":
        return redirect("dashboard:orders")
    return redirect("dashboard:order_detail", pk=pk)


@staff_required
def customers(request):
    query = request.GET.get("q", "").strip()
    qs = User.objects.filter(is_staff=False).annotate(
        order_count=Count("orders", distinct=True),
        spent=Sum("orders__total", filter=Q(orders__status__in=COUNTED_STATUSES)),
    )
    if query:
        qs = qs.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
    page = Paginator(qs.order_by("-date_joined"), 20).get_page(request.GET.get("page"))
    return render(request, "dashboard/customers.html", {"page_obj": page, "query": query, "section": "customers"})


@staff_required
def inventory(request):
    query = request.GET.get("q", "").strip()
    stock_filter = request.GET.get("stock", "")
    qs = Product.objects.select_related("category")
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(category__name__icontains=query))
    if stock_filter == "low":
        qs = qs.filter(stock__gt=0, stock__lte=settings.LOW_STOCK_THRESHOLD)
    elif stock_filter == "out":
        qs = qs.filter(stock=0)
    page = Paginator(qs.order_by("stock", "name"), 25).get_page(request.GET.get("page"))
    context = {
        "page_obj": page,
        "query": query,
        "stock_filter": stock_filter,
        "category_count": Category.objects.count(),
        "section": "inventory",
    }
    return render(request, "dashboard/inventory.html", context)
