from django.middleware.locale import LocaleMiddleware
from django.conf import settings
from django.conf.urls.i18n import is_language_prefix_patterns_used
from django.utils import translation


class CustomLocaleMiddleware(LocaleMiddleware):
    def process_request(self, request):
        urlconf = getattr(request, "urlconf", settings.ROOT_URLCONF)
        (
            i18n_patterns_used,
            prefixed_default_language,
        ) = is_language_prefix_patterns_used(urlconf)
        language = translation.get_language_from_request(
            request, check_path=i18n_patterns_used
        )
        language_from_path = translation.get_language_from_path(request.path_info)
        # In order to skip the preferred browser language, you can add Force_language = True to your settings.
        if settings.FORCE_LANGUAGES:
            if not language_from_path:
                language = settings.LANGUAGE_CODE
        else:
            if (
                not language_from_path
                and i18n_patterns_used
                and not prefixed_default_language
            ):
                language = settings.LANGUAGE_CODE
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()
