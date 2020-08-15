from django.contrib import admin, messages

from .models import Config
from .forms import ConfigAdminForm


@admin.register(Config)
class ConfigModelAdmin(admin.ModelAdmin):
    form = ConfigAdminForm
    list_display = ('name', 'data_type')

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super(ConfigModelAdmin, self).get_form(request, obj, change, **kwargs)
        if obj is not None:
            form.base_fields['raw_value'].initial = obj.value
        return form

    def save_model(self, request, obj, form, change):
        raw_value = form.cleaned_data.get('raw_value')
        data_type = form.cleaned_data.get('data_type')
        try:
            if data_type is not None and raw_value is not None:
                data = eval(f"{data_type}({raw_value})")
                obj.value = data
            return super(ConfigModelAdmin, self).save_model(request, obj, form, change)
        except Exception:
            return messages.error(request, 'Enter your raw value in the shape of entered data type')
