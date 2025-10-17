from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from hijack.contrib.admin import HijackUserAdminMixin  # NEW import

from .models import User


@admin.register(User)
class _UserAdmin(UserAdmin, HijackUserAdminMixin):
    pass
