from django.conf import settings
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from .forms import UserAdminChangeForm
from .forms import UserAdminCreationForm
from .models import User, PreRegisteredUser

from urban_performance.users.tasks import send_allow_registration

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow:
    # https://docs.allauth.org/en/latest/common/admin.html#admin
    admin.site.login = login_required(admin.site.login)  # type: ignore[method-assign]


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("name",)}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = ["email", "name", "is_superuser"]
    search_fields = ["name"]
    ordering = ["id"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )


class PreRegisteredUserAdmin(admin.ModelAdmin):
    list_display = ("email", "is_confirmed", "is_authorized", "created_at")
    list_filter = ("is_confirmed", "is_authorized")
    actions = ["authorize_selected"]

    def authorize_selected(self, request, queryset):
        for pre_user in queryset:
            pre_user.is_authorized = True
            pre_user.save()
            register_url = request.build_absolute_uri(reverse("account_signup"))
            send_allow_registration.delay(pre_user.pk, register_url)

    authorize_selected.short_description = "Authorize selected users"


admin.site.register(PreRegisteredUser, PreRegisteredUserAdmin)
