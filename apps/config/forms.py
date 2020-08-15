from django import forms
from .models import Config


class ConfigAdminForm(forms.ModelForm):
    raw_value = forms.CharField(widget=forms.Textarea())

    class Meta:
        model = Config
        fields = ['name', 'raw_value', 'data_type']
