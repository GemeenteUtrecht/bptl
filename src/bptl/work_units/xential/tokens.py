from datetime import date

from django.conf import settings
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.http import base36_to_int, int_to_base36

from bptl.work_units.xential.models import XentialTicket


class XentialTicketTokenGenerator:
    """
    Strategy object used to generate and check tokens for the retrieval of Xential URLs
    to build documents interactively.
    Implementation adapted from
    :class:`from django.contrib.auth.tokens.PasswordResetTokenGenerator`

    """

    key_salt = "bptl.work_units.xential.tokens.XentialTicketTokenGenerator"
    secret = settings.SECRET_KEY

    def make_token(self, ticket: XentialTicket) -> str:
        """
        Return a token that can be used once to retrieve the Xential interactive URL.
        """
        return self._make_token_with_timestamp(ticket, self._num_days(date.today()))

    def check_token(self, ticket: XentialTicket, token: str) -> bool:
        """
        Check that the token is correct for a given ticket.
        """

        if not (ticket and token):
            return False

        # parse the token
        try:
            ts_b36, _ = token.split("-")
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        valid_token = self._make_token_with_timestamp(ticket, ts)
        if not constant_time_compare(valid_token, token):
            return False

        # Check the timestamp is within limit. Timestamps are rounded to
        # midnight (server time) providing a resolution of only 1 day. If a
        # link is generated 5 minutes before midnight and used 6 minutes later,
        # that counts as 1 day. Therefore, XENTIAL_URL_TOKEN_TIMEOUT_DAYS = 1 means
        # "at least 1 day, could be up to 2."
        if (
            self._num_days(date.today()) - ts
        ) > settings.XENTIAL_URL_TOKEN_TIMEOUT_DAYS:
            return False

        return True

    def _make_token_with_timestamp(self, ticket: XentialTicket, timestamp: int) -> str:
        # timestamp is number of days since 2001-1-1.  Converted to
        # base 36, this gives us a 3 digit string until about 2121
        ts_b36 = int_to_base36(timestamp)
        hash_string = salted_hmac(
            self.key_salt,
            self._make_hash_value(ticket, timestamp),
            secret=self.secret,
        ).hexdigest()[
            ::2
        ]  # Limit to 20 characters to shorten the URL.
        return "%s-%s" % (ts_b36, hash_string)

    def _make_hash_value(self, ticket: XentialTicket, timestamp: int) -> str:
        """
        Hash the XentialTicket ID and some state properties.
        After a Xential document has been built and sent back to BPTL through
        a webhook, the state of the Xential ticket is changed, so the token
        will no longer validate.
        Failing that, eventually settings.XENTIAL_URL_TOKEN_TIMEOUT_DAYS will
        invalidate the token.
        TODO: possibly the expiry should be a parameter when the link is being
        generated.
        """
        ticket_attributes = (
            "ticket_uuid",
            "bptl_ticket_uuid",
            "is_ticket_complete",
        )
        task_attributes = ("id",)
        ticket_bits = [
            str(getattr(ticket, attribute) or "") for attribute in ticket_attributes
        ]
        task_bits = [
            str(getattr(ticket.task, attribute) or "") for attribute in task_attributes
        ]
        return "".join(ticket_bits + task_bits) + str(timestamp)

    def _num_days(self, dt) -> int:
        """
        Return the number of days between 01-01-2001 and today
        """
        return (dt - date(2001, 1, 1)).days


token_generator = XentialTicketTokenGenerator()
