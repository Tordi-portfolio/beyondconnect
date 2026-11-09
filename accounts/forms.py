from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Profile

User = get_user_model()


class StyledFormMixin:
    """Adds the site's CSS class to every widget."""

    def style_fields(self):
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


class SignUpForm(StyledFormMixin, UserCreationForm):
    first_name = forms.CharField(max_length=150, label="First name")
    last_name = forms.CharField(max_length=150, label="Last name")
    email = forms.EmailField(label="Email address")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()
        self.fields["first_name"].widget.attrs["placeholder"] = "Ada"
        self.fields["last_name"].widget.attrs["placeholder"] = "Okafor"
        self.fields["username"].widget.attrs["placeholder"] = "Choose a username"
        self.fields["email"].widget.attrs["placeholder"] = "you@example.com"
        self.fields["username"].help_text = "Letters, digits and @/./+/-/_ only."

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class LoginForm(StyledFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()
        self.fields["username"].label = "Username or email"
        self.fields["username"].widget.attrs.update({"placeholder": "Username or email", "autofocus": True})
        self.fields["password"].widget.attrs["placeholder"] = "Your password"


class UserUpdateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()
        self.fields["email"].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Another account already uses this email.")
        return email


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("phone", "address", "city")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()
