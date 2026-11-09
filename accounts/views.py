from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.views.decorators.http import require_POST

from store.models import Order, Product

from .forms import LoginForm, ProfileForm, SignUpForm, UserUpdateForm
from .models import Profile


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        # Staff land on the admin dashboard, customers on their own dashboard.
        if self.request.user.is_staff:
            return resolve_url("dashboard:home")
        return super().get_default_redirect_url()


def signup(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        Profile.for_user(user)
        login(request, user, backend="accounts.backends.EmailOrUsernameBackend")
        messages.success(request, f"Welcome to {settings.SITE_NAME}, {user.first_name}! Your account is ready.")
        return redirect("accounts:dashboard")
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def dashboard(request):
    orders = request.user.orders.prefetch_related("items")
    stats = orders.aggregate(
        count=Count("id"),
        spent=Sum("total", filter=~Q(status=Order.CANCELLED)),
    )
    active_orders = orders.filter(
        status__in=[Order.PENDING, Order.PROCESSING, Order.SHIPPED]
    ).count()
    deals = (
        Product.objects.filter(is_active=True, discount_percent__gt=0, stock__gt=0)
        .select_related("category")
        .order_by("-discount_percent")[:4]
    )
    context = {
        "recent_orders": orders[:5],
        "order_count": stats["count"] or 0,
        "total_spent": stats["spent"] or 0,
        "active_orders": active_orders,
        "deals": deals,
        "profile": Profile.for_user(request.user),
    }
    return render(request, "accounts/dashboard.html", context)


@login_required
def profile(request):
    profile_obj = Profile.for_user(request.user)
    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user, prefix="user")
        profile_form = ProfileForm(request.POST, instance=profile_obj, prefix="profile")
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("accounts:profile")
    else:
        user_form = UserUpdateForm(instance=request.user, prefix="user")
        profile_form = ProfileForm(instance=profile_obj, prefix="profile")
    return render(request, "accounts/profile.html", {"user_form": user_form, "profile_form": profile_form})


@login_required
def order_list(request):
    paginator = Paginator(request.user.orders.prefetch_related("items"), 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "accounts/order_list.html", {"page_obj": page})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(request.user.orders.prefetch_related("items"), pk=pk)
    return render(request, "accounts/order_detail.html", {"order": order})


@login_required
@require_POST
def cancel_order(request, pk):
    order = get_object_or_404(request.user.orders, pk=pk)
    if order.status == Order.PENDING:
        order.set_status(Order.CANCELLED)
        messages.success(request, f"Order {order.reference} was cancelled.")
    else:
        messages.error(request, "Only pending orders can be cancelled. Please contact us for help.")
    return redirect("accounts:order_detail", pk=order.pk)
