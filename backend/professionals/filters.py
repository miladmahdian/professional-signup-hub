import django_filters

from .models import Professional


class ProfessionalFilter(django_filters.FilterSet):
    class Meta:
        model = Professional
        fields = ['source']
