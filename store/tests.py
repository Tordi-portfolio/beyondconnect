from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Category, Order, Product

User = get_user_model()


def make_product(name="Test Laptop", price="100.00", discount=0, stock=5, category=None, **kwargs):
    category = category or Category.objects.get_or_create(name="Electronics")[0]
    return Product.objects.create(
        category=category, name=name, description=kwargs.pop("description", f"About {name}"),
        price=Decimal(price), discount_percent=discount, stock=stock, **kwargs,
    )


class PricingTests(TestCase):
    def test_discounted_price(self):
        p = make_product(price="100.00", discount=25)
        self.assertEqual(p.discounted_price, Decimal("75.00"))
        self.assertEqual(p.savings, Decimal("25.00"))
        self.assertTrue(p.has_discount)

    def test_no_discount(self):
        p = make_product(price="19.99", discount=0)
        self.assertEqual(p.discounted_price, Decimal("19.99"))
        self.assertFalse(p.has_discount)

    def test_slug_is_unique(self):
        a = make_product(name="Same Name")
        b = make_product(name="Same Name")
        self.assertNotEqual(a.slug, b.slug)


class SearchTests(TestCase):
    def setUp(self):
        self.laptop = make_product(name="Aero Laptop", discount=10)
        self.shoes = make_product(name="Running Shoes", category=Category.objects.create(name="Sports"))
        self.hidden = make_product(name="Secret Laptop", is_active=False)

    def test_search_returns_matching_products_only(self):
        response = self.client.get(reverse("store:search"), {"q": "laptop"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aero Laptop")
        self.assertNotContains(response, "Running Shoes")
        self.assertNotContains(response, "Secret Laptop")

    def test_search_matches_category_name(self):
        response = self.client.get(reverse("store:search"), {"q": "sports"})
        self.assertContains(response, "Running Shoes")

    def test_no_results_message(self):
        response = self.client.get(reverse("store:search"), {"q": "zzzz"})
        self.assertContains(response, "No products found")

    def test_sort_by_price(self):
        make_product(name="Cheap Laptop", price="10.00")
        response = self.client.get(reverse("store:search"), {"q": "laptop", "sort": "price_low"})
        names = [p.name for p in response.context["products"]]
        self.assertEqual(names[0], "Cheap Laptop")

    def test_suggestions_endpoint(self):
        response = self.client.get(reverse("store:suggest"), {"q": "aero"})
        self.assertEqual(response.json()["results"][0]["name"], "Aero Laptop")


class CartAndCheckoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("buyer", "buyer@example.com", "pass12345!", first_name="Bola")
        self.product = make_product(price="40.00", discount=50, stock=3)  # sells at 20.00

    def test_add_to_cart_clamps_to_stock(self):
        self.client.post(reverse("store:add_to_cart", args=[self.product.pk]), {"quantity": 10})
        response = self.client.get(reverse("store:cart"))
        self.assertEqual(response.context["cart"].lines[0]["quantity"], 3)

    def test_checkout_requires_login(self):
        response = self.client.get(reverse("store:checkout"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_checkout_creates_order_and_reduces_stock(self):
        self.client.login(username="buyer", password="pass12345!")
        self.client.post(reverse("store:add_to_cart", args=[self.product.pk]), {"quantity": 2})
        response = self.client.post(reverse("store:checkout"), {
            "full_name": "Bola Ade", "email": "buyer@example.com", "phone": "08012345678",
            "address": "12 Main Street", "city": "Lagos", "payment_method": "cod", "notes": "",
        })
        order = Order.objects.get()
        self.assertRedirects(response, reverse("store:order_success", args=[order.pk]))
        self.assertEqual(order.subtotal, Decimal("40.00"))
        self.assertEqual(order.items.get().unit_price, Decimal("20.00"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

    def test_cancelling_order_restocks(self):
        self.client.login(username="buyer", password="pass12345!")
        self.client.post(reverse("store:add_to_cart", args=[self.product.pk]), {"quantity": 2})
        self.client.post(reverse("store:checkout"), {
            "full_name": "Bola Ade", "email": "buyer@example.com", "phone": "1",
            "address": "12 Main Street", "city": "Lagos", "payment_method": "cod",
        })
        order = Order.objects.get()
        self.client.post(reverse("accounts:cancel_order", args=[order.pk]))
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, Order.CANCELLED)
        self.assertEqual(self.product.stock, 3)


class WhatsAppTests(TestCase):
    def test_success_page_links_to_whatsapp_with_item_and_description(self):
        user = User.objects.create_user("wa", "wa@example.com", "pass12345!")
        product = make_product(name="Aero Laptop", price="100.00", stock=5, description="Light 14-inch laptop")
        self.client.login(username="wa", password="pass12345!")
        self.client.post(reverse("store:add_to_cart", args=[product.pk]), {"quantity": 1})
        response = self.client.post(reverse("store:checkout"), {
            "full_name": "Wale A", "email": "wa@example.com", "phone": "0801",
            "address": "1 Road", "city": "Lagos", "payment_method": "cod",
        }, follow=True)
        self.assertTrue(response.context["auto_redirect"])
        url = response.context["whatsapp_url"]
        self.assertTrue(url.startswith("https://wa.me/2347068848255?text="))
        self.assertIn("Aero%20Laptop", url)
        self.assertIn("Light%2014-inch%20laptop", url)
        # Revisiting the page must not auto-redirect again.
        order = Order.objects.get()
        again = self.client.get(reverse("store:order_success", args=[order.pk]))
        self.assertFalse(again.context["auto_redirect"])


class ProductAdminTests(TestCase):
    def test_changelist_and_add_pages_load(self):
        User.objects.create_superuser("root", "root@example.com", "pass12345!")
        self.client.login(username="root", password="pass12345!")
        make_product()
        self.assertEqual(self.client.get(reverse("admin:store_product_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:store_product_add")).status_code, 200)


class AccountTests(TestCase):
    def test_signup_logs_user_in_and_shows_dashboard(self):
        response = self.client.post(reverse("accounts:signup"), {
            "first_name": "Ada", "last_name": "Obi", "username": "ada", "email": "ada@example.com",
            "password1": "Str0ng-Pass-99", "password2": "Str0ng-Pass-99",
        }, follow=True)
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.assertTrue(response.context["user"].is_authenticated)

    def test_duplicate_email_rejected(self):
        User.objects.create_user("first", "dup@example.com", "pass12345!")
        response = self.client.post(reverse("accounts:signup"), {
            "first_name": "B", "last_name": "C", "username": "second", "email": "DUP@example.com",
            "password1": "Str0ng-Pass-99", "password2": "Str0ng-Pass-99",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="second").exists())

    def test_login_with_email(self):
        User.objects.create_user("tola", "tola@example.com", "pass12345!")
        response = self.client.post(reverse("accounts:login"), {"username": "tola@example.com", "password": "pass12345!"})
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 302)


class AdminDashboardTests(TestCase):
    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 302)

    def test_customer_forbidden(self):
        User.objects.create_user("cust", "c@example.com", "pass12345!")
        self.client.login(username="cust", password="pass12345!")
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 403)

    def test_staff_can_view_all_pages(self):
        User.objects.create_user("boss", "boss@example.com", "pass12345!", is_staff=True)
        make_product()
        self.client.login(username="boss", password="pass12345!")
        for name in ("home", "orders", "customers", "inventory"):
            self.assertEqual(self.client.get(reverse(f"dashboard:{name}")).status_code, 200, name)
