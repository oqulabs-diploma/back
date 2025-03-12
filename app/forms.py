from typing import Any, Type

from django.forms import (
    EmailField,
    CharField,
    ModelForm,
    Form,
    ValidationError,
)
from django.contrib.auth.models import User


class UserForgotPasswordForm(Form):
    """User form for password recovery process."""

    email: EmailField = EmailField(required=True)


class UserForgotPasswordFormStep2(Form):
    """User form for password recovery process."""
    """Step 2: email and token"""

    email: EmailField = EmailField(required=True)
    token: CharField = CharField(required=True)
    new_password: CharField = CharField(required=True)


class UserRegistrationModelForm(ModelForm):
    """User form for registration process."""

    email: EmailField = EmailField(required=True)
    first_name: CharField = CharField(required=True)
    last_name: CharField = CharField(required=True)
    password: CharField = CharField(required=True)

    class Meta:
        """Meta class for the form customization."""

        model: Type[User] = User
        fields: tuple[str, ...] = (
            "email",
            "first_name",
            "last_name",
            "password",
        )

    def clean_email(self) -> str:
        """Validate that the user with provided email does not exist."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("User already exists")
        return email

    def save(self, commit=True) -> User:
        """Save the user but set username = email."""

        user: User = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.username = self.cleaned_data['email']
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserLoginModelForm(ModelForm):
    """User form for login process."""

    email: EmailField = EmailField(required=True)
    password: CharField = CharField(required=True)

    def clean(self) -> dict[str, Any]:
        """Validate that the user with provided email exists and password is correct."""

        email: str = self.cleaned_data.get('email')
        if not User.objects.filter(email=email.lower()).exists():
            raise ValidationError({"email": "User not found"})

        password: str = self.cleaned_data.get('password')
        user: User = User.objects.get(email=email.lower())
        if not user.check_password(password):
            raise ValidationError({ "password": "Invalid password" })

        self.cleaned_data["user"] = user
        return super().clean()

    class Meta:
        """Meta class for the form customization."""
        model: Type[User] = User
        fields: tuple[str, ...] = (
            "email",
            "password",
        )
