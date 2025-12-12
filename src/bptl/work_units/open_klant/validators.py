from email.errors import HeaderParseError
from email.headerregistry import Address

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class RFC5322EmailValidator:
    """
    Drop-in replacement for django.core.validators.EmailValidator,
    but using Python's RFC5322-aware parser and allowing '&' etc.
    """

    message = "Enter a valid email address."
    code = "invalid"

    def __call__(self, value):
        if value is None:
            raise ValidationError(self.message, code=self.code)

        value = value.strip()

        try:
            # Force it to be a bare addr-spec, not "Name <addr>"
            addr = Address(addr_spec=value)
        except (HeaderParseError, ValueError):
            raise ValidationError(self.message, code=self.code)

        # Optional: enforce that what was typed is a clean addr-spec.
        # This keeps behaviour predictable and avoids weird legacy syntax.
        if addr.addr_spec != value:
            raise ValidationError(self.message, code=self.code)
