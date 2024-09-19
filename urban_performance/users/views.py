from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import UpdateView
from django.views.generic import CreateView
from django.views.generic import View

from urban_performance.users.models import User, PreRegisteredUser
from urban_performance.users.tasks import send_confirmation_url


from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import RedirectView


class BlockIfAuthenticated(UserPassesTestMixin, RedirectView):
    def test_func(self):
        return not self.request.user.is_authenticated


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "id"
    slug_url_kwarg = "id"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self):
        # for mypy to know that the user is authenticated
        assert self.request.user.is_authenticated
        return self.request.user.get_absolute_url()

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail", kwargs={"pk": self.request.user.pk})


user_redirect_view = UserRedirectView.as_view()


class PreRegisterView(CreateView, BlockIfAuthenticated):
    model = PreRegisteredUser
    fields = ["email"]
    success_url = "users:pre_register"

    def create_pre_register(self, email, token):
        user = User.objects.filter(email=email)
        if user.exists():
            messages.error(
                self.request, _("Please use another email.")
            )
            return

        pre_user, created = PreRegisteredUser.objects.get_or_create(email=email)
        if pre_user.is_authorized:
            messages.error(
                self.request, _("The email is already registered and authorized to use.")
            )
            return
        elif pre_user.is_confirmed:
            messages.warning(
                self.request, _("The email is already in wait list.")
            )
            return

        pre_user.confirmation_token = token
        pre_user.save()

        confirmation_url = self.request.build_absolute_uri(
            reverse("users:confirm_email", args=[token])
        )
        # print(confirmation_url)
        send_confirmation_url.delay(pre_user.pk, confirmation_url)
        messages.success(
            self.request,
            _("An email has been sent to: %(email)s, please check your inbox in order to confirm your email!") % {"email": email},    
        )

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        token = get_random_string(length=64)
        self.create_pre_register(email=email, token=token)
        return redirect(reverse(self.success_url))

    def form_invalid(self, form):
        email = form.data["email"]
        token = get_random_string(length=64)
        # Add an additional validation to check if the form fails because there is already a register.
        try:
            PreRegisteredUser.objects.get(email=email)
        except PreRegisteredUser.DoesNotExist:
            messages.error(
                self.request, _("The email introduced is incorrect. Please check it.")
            )
        self.create_pre_register(email=email, token=token)
        return redirect(reverse(self.success_url))


class ConfirmEmailView(View):
    def get(self, request, *args, **kwargs):
        try:
            pre_user = PreRegisteredUser.objects.get(
                confirmation_token=self.kwargs.get("token", "")
            )
            pre_user.is_confirmed = True
            pre_user.save()
            messages.success(
                request,
                _("The email %(email)s, has been validated, once an admin reviews your request you will be able to register.") % {"email": pre_user.email},
            )
            return redirect("projects:project_list")
        except PreRegisteredUser.DoesNotExist:
            messages.error(
                request,
                _("The token provided is not valid or expired, please try to pre-register again."),
            )
            return redirect("users:pre_register")
