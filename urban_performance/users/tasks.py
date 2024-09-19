from celery import shared_task

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

from urban_performance.users.models import PreRegisteredUser


@shared_task()
def send_allow_registration(pre_user_pk, register_url):
    # 1. HTML Email Template
    pre_user = PreRegisteredUser.objects.get(pk=pre_user_pk)
    subject = "Your registration is authorized"
    html_content = render_to_string(
        "emails/allow_registration.html",
        {
            "pre_user": pre_user,
            "register_url": register_url,
        },
    )

    # 2. Email Creation and Sending
    email = EmailMultiAlternatives(
        subject,
        html_content,
        settings.EMAIL_SENDER,
        [pre_user.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)


@shared_task()
def send_confirmation_url(pre_user_pk, confirmation_url):
    # 1. HTML Email Template
    pre_user = PreRegisteredUser.objects.get(pk=pre_user_pk)
    subject = "Please confirm your email!"
    html_content = render_to_string(
        "emails/email_confirmation.html",
        {
            "pre_user": pre_user,
            "confirmation_url": confirmation_url,
        },
    )

    # 2. Email Creation and Sending
    email = EmailMultiAlternatives(
        subject,
        html_content,
        settings.EMAIL_SENDER,
        [pre_user.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)