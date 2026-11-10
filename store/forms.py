from django import forms

from .models import Order, Testimonial


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

class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ("name", "location", "item", "message")
        labels = {
            "name": "Your name",
            "location": "Your city / state",
            "item": "What did you order? (optional)",
            "message": "Your experience",
        }
        widgets = {
            "message": forms.Textarea(attrs={"rows": 5, "placeholder": "Tell us about your order and how your delivery went…"}),
            "location": forms.TextInput(attrs={"placeholder": "e.g. Lagos"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")

    def clean_message(self):
        message = self.cleaned_data["message"].strip()
        if len(message) < 20:
            raise forms.ValidationError("Please write at least a sentence or two (20 characters).")
        return message