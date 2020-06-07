from django.forms import ModelForm, PasswordInput
from django import forms

from .models import InstagramAccount


class InstagramAccountForm(ModelForm):
    password = forms.CharField(widget=PasswordInput())

    class Meta:
        fields = "__all__"
        model = InstagramAccount
