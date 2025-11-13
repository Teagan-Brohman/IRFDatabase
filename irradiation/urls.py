from django.urls import path
from . import views

app_name = 'irradiation'

urlpatterns = [
    # Home page
    path('', views.home, name='home'),

    # IRF views
    path('irfs/', views.IRFListView.as_view(), name='irf_list'),
    path('irf/<int:pk>/', views.IRFDetailView.as_view(), name='irf_detail'),
    path('irf/new/', views.IRFCreateView.as_view(), name='irf_create'),
    path('irf/<int:pk>/edit/', views.IRFUpdateView.as_view(), name='irf_update'),

    # Sample log views
    path('sample-log/new/', views.SampleLogCreateView.as_view(), name='sample_log_create'),

    # API endpoints
    path('api/irf-autocomplete/', views.irf_autocomplete, name='irf_autocomplete'),
]
