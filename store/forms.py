from django import forms

from .models import Order


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ("full_name", "email", "phone", "address", "city", "payment_method", "notes")
        widgets = {
            "address": forms.TextInput(attrs={"placeholder": "Street address"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Delivery instructions (optional)"}),
            "payment_method": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "payment_method":
                field.widget.attrs.setdefault("class", "input")
