from django import forms
from django.core.exceptions import ValidationError

from .models import Config


class ConfigAdminForm(forms.ModelForm):
    raw_value = forms.CharField(widget=forms.Textarea())

    class Meta:
        model = Config
        fields = ['name', 'raw_value', 'data_type']

    def clean(self):
        raw_value = self.cleaned_data.get('raw_value')
        data_type = self.cleaned_data.get('data_type')
        try:
            data = eval(f"{data_type}({raw_value})")
            self.cleaned_data.update({"raw_value": data})
        except Exception:
            raise ValidationError('Enter your raw value in the shape of entered data type')
