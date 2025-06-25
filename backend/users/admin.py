from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ExtendedUser


class ExtendedUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name')
    ordering = ('email',)


admin.site.register(ExtendedUser, ExtendedUserAdmin)
