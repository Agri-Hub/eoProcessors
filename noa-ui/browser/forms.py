from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class NoaUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True, help_text="You must use your @noa email address."
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"]
        domain = email.split("@")[-1]
        if not domain.lower().startswith("noa"):
            raise ValidationError("Registration is only allowed with a @noa email.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("That email is already in use.")
        return email
