from django.urls import path

from . import views

app_name = "store"

urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.product_list, name="product_list"),
    path("search/", views.product_list, name="search"),
    path("search/suggest/", views.search_suggestions, name="suggest"),
    path("category/<slug:category_slug>/", views.product_list, name="category"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:product_id>/", views.update_cart, name="update_cart"),
    path("cart/remove/<int:product_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("order/<int:pk>/success/", views.order_success, name="order_success"),

    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("testimonials/", views.testimonials, name="testimonials"),
]
