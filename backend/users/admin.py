from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AuthenticationForm
from django import forms

from .models import ExtendedUser


class EmailAdminAuthForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email", 
        widget=forms.EmailInput(attrs={'autofocus': True})
    )

    def clean_username(self):
        return self.cleaned_data['username']


class ExtendedUserAdmin(UserAdmin):
    login_form = EmailAdminAuthForm
    list_display = ('email', 'first_name', 'last_name')
    ordering = ('email',)


admin.site.register(ExtendedUser, ExtendedUserAdmin)
