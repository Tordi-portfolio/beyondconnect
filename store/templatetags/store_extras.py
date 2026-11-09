from decimal import Decimal, InvalidOperation

from django import template
from django.conf import settings

register = template.Library()


@register.filter
def money(value):
    """Format a number as currency, e.g. 1234.5 -> ₦1,234.50 (symbol set in settings.CURRENCY_SYMBOL)."""
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    return f"{settings.CURRENCY_SYMBOL}{amount:,.2f}"


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """Return the current query string with some parameters replaced (used by pagination)."""
    query = context["request"].GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return query.urlencode()
