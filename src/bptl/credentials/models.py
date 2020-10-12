import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from zgw_consumers.constants import AuthTypes

logger = logging.getLogger(__name__)


class App(models.Model):
    label = models.CharField(
        _("label"), max_length=100, help_text=_("Human readable app identifier.")
    )
    app_id = models.CharField(
        _("app ID"),
        max_length=1000,
        unique=True,
        help_text=_(
            "(Globally) unique application identifier. Typically the "
            "URL of the application in the Autorisaties API."
        ),
    )

    class Meta:
        verbose_name = _("application")
        verbose_name_plural = _("applications")

    def __str__(self):
        return self.label


class AppServiceCredentials(models.Model):
    """
    Connect an App to a Service with app-specific credentials.
    """

    # relational data - connect app to service and vice versa
    app = models.ForeignKey(
        "App",
        on_delete=models.CASCADE,
        verbose_name=_("application"),
    )
    service = models.ForeignKey(
        "zgw_consumers.Service",
        on_delete=models.CASCADE,
        verbose_name=_("service"),
        help_text=_("External service to configure credentials for."),
    )

    # store the required credentials
    # TODO: use encryption extensions for these fields

    # ZGW client ID + secret
    client_id = models.CharField(max_length=255, blank=True)
    secret = models.CharField(max_length=255, blank=True)

    # API key of sorts
    header_key = models.CharField(_("header key"), max_length=100, blank=True)
    header_value = models.CharField(_("header value"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("service credentials")
        verbose_name_plural = _("service credentials")
        constraints = (
            models.UniqueConstraint(
                fields=["app", "service"], name="unique_app_service"
            ),
        )

    def __str__(self):
        return _("Credentials for {app} on {service}").format(
            app=self.app, service=self.service
        )

    def clean(self):
        super().clean()

        zgw_fields = (self.client_id, self.secret)
        api_key_fields = (self.header_key, self.header_value)

        # validate the credential setup
        if self.service:
            auth_type = self.service.auth_type

            if auth_type == AuthTypes.no_auth and any((*zgw_fields, *api_key_fields)):
                raise ValidationError(
                    _(
                        "The service has '{auth_type}' type of authorization. You should not enter "
                        "any credentials at all."
                    ).format(auth_type=self.service.get_auth_type_display()),
                    code="no-auth",
                )
            elif auth_type == AuthTypes.zgw and not all(zgw_fields):
                raise ValidationError(
                    _(
                        "The service has '{auth_type}' type of authorization. You must fill "
                        "out the client_id and secret."
                    ).format(auth_type=self.service.get_auth_type_display()),
                    code="incomplete-auth",
                )
            elif auth_type == AuthTypes.api_key and not all(api_key_fields):
                raise ValidationError(
                    _(
                        "The service has '{auth_type}' type of authorization. You must fill "
                        "out the header key and value."
                    ).format(auth_type=self.service.get_auth_type_display()),
                    code="incomplete-auth",
                )
            else:
                logger.warning("Unknown service auth_type specified: %s", auth_type)
