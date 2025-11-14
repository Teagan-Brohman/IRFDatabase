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
    path('sample-log/<int:pk>/edit/', views.SampleLogUpdateView.as_view(), name='sample_log_update'),
    path('sample-log/<int:pk>/delete/', views.SampleLogDeleteView.as_view(), name='sample_log_delete'),

    # Sample views
    path('samples/', views.SampleListView.as_view(), name='sample_list'),
    path('samples/combo/', views.ComboSampleListView.as_view(), name='combo_sample_list'),
    path('sample/<int:pk>/', views.SampleDetailView.as_view(), name='sample_detail'),
    path('sample/new/', views.SampleCreateView.as_view(), name='sample_create'),
    path('sample/<int:pk>/edit/', views.SampleUpdateView.as_view(), name='sample_update'),
    path('sample/combo/new/', views.ComboSampleCreateView.as_view(), name='combo_sample_create'),

    # API endpoints
    path('api/irf-autocomplete/', views.irf_autocomplete, name='irf_autocomplete'),
    path('api/sample-autocomplete/', views.sample_autocomplete, name='sample_autocomplete'),
    path('api/sample/<int:pk>/calculate-isotopics/', views.calculate_sample_isotopics, name='calculate_isotopics'),
]
