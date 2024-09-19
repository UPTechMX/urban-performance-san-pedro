from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.db.models import EmailField
from django.db.models import BooleanField
from django.db.models import DateTimeField
from django.db.models import Model
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


from .managers import UserManager


class User(AbstractUser):
    """
    Default custom user model for urban_performance.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})


class PreRegisteredUser(Model):
    email = EmailField(unique=True)
    is_confirmed = BooleanField(default=False)
    is_authorized = BooleanField(default=False)
    confirmation_token = CharField(max_length=64, unique=True, blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
