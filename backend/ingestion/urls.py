from django.urls import path
from . import views

urlpatterns = [
    # Tenants
    path('tenants/', views.TenantListView.as_view()),

    # Upload
    path('upload/', views.UploadView.as_view()),

    # Data sources
    path('sources/', views.DataSourceListView.as_view()),

    # Emission records
    path('records/', views.EmissionRecordListView.as_view()),
    path('records/<uuid:pk>/', views.EmissionRecordDetailView.as_view()),
    path('records/<uuid:pk>/review/', views.ReviewActionView.as_view()),
    path('records/<uuid:pk>/audit/', views.AuditLogView.as_view()),
    path('records/bulk-review/', views.BulkReviewView.as_view()),

    # Dashboard
    path('dashboard/', views.DashboardStatsView.as_view()),
]
