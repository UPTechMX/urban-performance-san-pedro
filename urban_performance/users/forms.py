from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django.contrib.auth import forms as admin_forms
from django.forms import EmailField, TextInput, PasswordInput
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .models import User, PreRegisteredUser


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User
        field_classes = {"email": EmailField}


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):
        model = User
        fields = ("email",)
        field_classes = {"email": EmailField}
        error_messages = {
            "email": {"unique": _("This email has already been taken.")},
        }


class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """
    def __init__(self, *args, **kwargs):
        super(UserSignupForm, self).__init__(*args, **kwargs)
        self.fields['email'].widget = TextInput(attrs={'type': 'email', 'class': 'borders-secondary'})
        self.fields['password1'].widget = PasswordInput(attrs={'class': 'borders-secondary'})
        self.fields['password2'].widget = PasswordInput(attrs={'class': 'borders-secondary'})

    def clean_email(self):
        email = self.cleaned_data['email']

        if not self.is_allowed_email(email):
            raise ValidationError("This email is not allowed to register. ")

        return super().clean_email()

    
    def is_allowed_email(self, email):
        pre_user, created = PreRegisteredUser.objects.get_or_create(email=email)
        if pre_user.is_authorized:
            return True
        elif created:
            pre_user.delete()
        return False
            


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """

from allauth.account.forms import LoginForm

class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super(CustomLoginForm, self).__init__(*args, **kwargs)
        self.fields['login'].widget = TextInput(attrs={'type': 'email', 'class': 'borders-secondary'})
        self.fields['password'].widget = PasswordInput(attrs={'class': 'borders-secondary'})