import django_filters

from .models import Professional


class ProfessionalFilter(django_filters.FilterSet):
    source = django_filters.CharFilter(field_name='source', lookup_expr='exact')

    class Meta:
        model = Professional
        fields = ['source']
