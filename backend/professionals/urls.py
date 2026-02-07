from django.urls import path

from .views import ProfessionalListCreateView

urlpatterns = [
    path('', ProfessionalListCreateView.as_view(), name='professional-list-create'),
]
