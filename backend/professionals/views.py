from rest_framework import generics

from .models import Professional
from .serializers import ProfessionalSerializer
from .filters import ProfessionalFilter


class ProfessionalListCreateView(generics.ListCreateAPIView):
    """GET /api/professionals/ — list all (with optional ?source= filter)
    POST /api/professionals/ — create a single professional"""

    queryset = Professional.objects.all()
    serializer_class = ProfessionalSerializer
    filterset_class = ProfessionalFilter
