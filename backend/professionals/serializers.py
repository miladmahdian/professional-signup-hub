from rest_framework import serializers

from .models import Professional


class ProfessionalSerializer(serializers.ModelSerializer):
    """Used for single create and list responses.
    Includes DRF's automatic unique validators for email and phone."""

    class Meta:
        model = Professional
        fields = '__all__'


class BulkProfessionalItemSerializer(serializers.ModelSerializer):
    """Used for each item in the bulk upsert endpoint.
    Removes unique validators on email and phone so that existing records
    pass validation — uniqueness is handled manually in the upsert logic."""

    class Meta:
        model = Professional
        fields = '__all__'
        extra_kwargs = {
            'email': {'validators': []},
            'phone': {'validators': []},
        }
