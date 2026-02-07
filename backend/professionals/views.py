from django.db import IntegrityError
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Professional
from .serializers import BulkProfessionalItemSerializer, ProfessionalSerializer
from .filters import ProfessionalFilter


class ProfessionalListCreateView(generics.ListCreateAPIView):
    """GET /api/professionals/ — list all (with optional ?source= filter)
    POST /api/professionals/ — create a single professional"""

    queryset = Professional.objects.all()
    serializer_class = ProfessionalSerializer
    filterset_class = ProfessionalFilter


class ProfessionalBulkUpsertView(APIView):
    """POST /api/professionals/bulk — bulk upsert with partial success.
    Uses email as the primary lookup key, falls back to phone if no email."""

    def post(self, request):
        if not isinstance(request.data, list):
            return Response(
                {'detail': 'Expected a list of professional objects.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = []
        updated = []
        errors = []

        for index, item in enumerate(request.data):
            # Step 1: Validate fields
            serializer = BulkProfessionalItemSerializer(data=item)
            if not serializer.is_valid():
                errors.append({
                    'index': index,
                    'data': item,
                    'errors': serializer.errors,
                })
                continue

            validated = serializer.validated_data

            # Step 2: Determine lookup key
            email = validated.get('email')
            phone = validated.get('phone')

            if not email and not phone:
                errors.append({
                    'index': index,
                    'data': item,
                    'errors': {'non_field_errors': ['Either email or phone is required.']},
                })
                continue

            # Step 3: Look up existing record
            existing = None
            if email:
                existing = Professional.objects.filter(email=email).first()
            elif phone:
                existing = Professional.objects.filter(phone=phone).first()

            # Step 4: Create or update
            try:
                if existing:
                    for field, value in validated.items():
                        setattr(existing, field, value)
                    existing.save()
                    updated.append({
                        'index': index,
                        'professional': ProfessionalSerializer(existing).data,
                    })
                else:
                    new_professional = Professional.objects.create(**validated)
                    created.append({
                        'index': index,
                        'professional': ProfessionalSerializer(new_professional).data,
                    })
            except IntegrityError as e:
                errors.append({
                    'index': index,
                    'data': item,
                    'errors': {'non_field_errors': [str(e)]},
                })

        return Response({
            'created': created,
            'updated': updated,
            'errors': errors,
        }, status=status.HTTP_200_OK)
