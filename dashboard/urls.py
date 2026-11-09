from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("orders/", views.orders, name="orders"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/status/", views.update_order_status, name="order_status"),
    path("customers/", views.customers, name="customers"),
    path("inventory/", views.inventory, name="inventory"),
]
