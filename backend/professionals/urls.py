from django.urls import path

from .views import ProfessionalBulkUpsertView, ProfessionalListCreateView

urlpatterns = [
    path('', ProfessionalListCreateView.as_view(), name='professional-list-create'),
    path('bulk', ProfessionalBulkUpsertView.as_view(), name='professional-bulk-upsert'),
]
