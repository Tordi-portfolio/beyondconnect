from urllib.parse import quote

from django.conf import settings

MAX_DESCRIPTION_CHARS = 200


def _money(value):
    return f"{settings.CURRENCY_SYMBOL}{value:,.2f}"


def build_order_message(order):
    """Plain-text WhatsApp message describing an order and each item ordered."""
    lines = [
        f"Hello {settings.SITE_NAME}, I just placed order {order.reference}.",
        "",
        "ITEMS ORDERED:",
    ]
    for index, item in enumerate(order.items.select_related("product"), start=1):
        lines.append(f"{index}. {item.product_name} x{item.quantity} - {_money(item.unit_price)} each = {_money(item.line_total)}")
        description = (item.product.description if item.product else "").strip()
        if description:
            if len(description) > MAX_DESCRIPTION_CHARS:
                description = description[: MAX_DESCRIPTION_CHARS - 1].rstrip() + "…"
            lines.append(f"   Description: {description}")

    lines += [
        "",
        f"Subtotal: {_money(order.subtotal)}",
        f"Delivery: {'Free' if order.shipping_fee == 0 else _money(order.shipping_fee)}",
        f"TOTAL: {_money(order.total)}",
        f"Payment: {order.get_payment_method_display()}",
        "",
        "DELIVERY DETAILS:",
        f"Name: {order.full_name}",
        f"Phone: {order.phone}",
        f"Address: {order.address}, {order.city}",
    ]
    if order.notes:
        lines.append(f"Notes: {order.notes}")
    return "\n".join(lines)


def build_whatsapp_url(order):
    number = "".join(ch for ch in str(settings.WHATSAPP_NUMBER) if ch.isdigit())
    return f"https://wa.me/{number}?text={quote(build_order_message(order))}"
