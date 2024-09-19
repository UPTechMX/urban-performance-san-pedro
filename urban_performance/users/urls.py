from django.urls import path

from .views import PreRegisterView, ConfirmEmailView

app_name = "users"
urlpatterns = [
    path('pre-register/', PreRegisterView.as_view(), name='pre_register'),
    path('confirm/<str:token>/', ConfirmEmailView.as_view(), name='confirm_email'),
    # path("~redirect/", view=user_redirect_view, name="redirect"),
    # path("~update/", view=user_update_view, name="update"),
    # path("<int:pk>/", view=user_detail_view, name="detail"),
]
