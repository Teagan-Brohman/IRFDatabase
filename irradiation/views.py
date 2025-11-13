from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.db.models import Q, Count
from django.urls import reverse_lazy
from .models import IrradiationRequestForm, SampleIrradiationLog


class IRFListView(ListView):
    """
    Main search/list view for IRFs
    User-friendly interface with search and filtering
    """
    model = IrradiationRequestForm
    template_name = 'irradiation/irf_list.html'
    context_object_name = 'irfs'
    paginate_by = 25

    def get_queryset(self):
        """Filter IRFs based on search query"""
        queryset = IrradiationRequestForm.objects.all().annotate(
            num_logs=Count('irradiation_logs')
        )

        # Search functionality
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(irf_number__icontains=query) |
                Q(sample_description__icontains=query) |
                Q(requester_name__icontains=query)
            )

        # Status filter
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)

        # Physical form filter
        physical_form = self.request.GET.get('physical_form', '')
        if physical_form:
            queryset = queryset.filter(physical_form=physical_form)

        # Year filter (from IRF number)
        year = self.request.GET.get('year', '')
        if year:
            queryset = queryset.filter(irf_number__startswith=year)

        return queryset

    def get_context_data(self, **kwargs):
        """Add filter options to context"""
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_physical_form'] = self.request.GET.get('physical_form', '')
        context['selected_year'] = self.request.GET.get('year', '')

        # Get unique years from IRF numbers for filter
        context['available_years'] = sorted(
            set(irf.irf_number.split('-')[0] for irf in IrradiationRequestForm.objects.all() if '-' in irf.irf_number),
            reverse=True
        )

        context['status_choices'] = IrradiationRequestForm.STATUS_CHOICES
        context['physical_form_choices'] = IrradiationRequestForm.PHYSICAL_FORM_CHOICES

        return context


class IRFDetailView(DetailView):
    """
    Detail view for a single IRF with tabs for:
    - IRF Details
    - Sample Irradiation Logs
    """
    model = IrradiationRequestForm
    template_name = 'irradiation/irf_detail.html'
    context_object_name = 'irf'

    def get_context_data(self, **kwargs):
        """Add sample logs to context"""
        context = super().get_context_data(**kwargs)
        context['sample_logs'] = self.object.irradiation_logs.all().order_by('-irradiation_date')
        context['active_tab'] = self.request.GET.get('tab', 'details')
        return context


class IRFCreateView(CreateView):
    """Create new IRF"""
    model = IrradiationRequestForm
    template_name = 'irradiation/irf_form.html'
    fields = [
        'irf_number', 'sample_description', 'physical_form', 'physical_form_other',
        'encapsulation', 'encapsulation_other', 'irradiation_location',
        'irradiation_location_other', 'max_power', 'max_time', 'max_mass',
        'expected_dose_rate', 'dose_rate_basis', 'dose_rate_reference_irf',
        'dose_rate_calculation_notes', 'reactivity_worth', 'reactivity_basis',
        'reactivity_reference_irf', 'request_comments', 'requester_name',
        'requester_signature_date'
    ]
    success_url = reverse_lazy('irradiation:irf_list')


class IRFUpdateView(UpdateView):
    """Update existing IRF"""
    model = IrradiationRequestForm
    template_name = 'irradiation/irf_form.html'
    fields = '__all__'

    def get_success_url(self):
        return reverse_lazy('irradiation:irf_detail', kwargs={'pk': self.object.pk})


class SampleLogCreateView(CreateView):
    """Create new sample irradiation log"""
    model = SampleIrradiationLog
    template_name = 'irradiation/sample_log_form.html'
    fields = [
        'irf', 'irradiation_date', 'sample_id', 'experimenter_name',
        'actual_location', 'actual_power', 'time_in', 'time_out',
        'total_time', 'measured_dose_rate', 'decay_time', 'operator_initials',
        'notes'
    ]

    def get_initial(self):
        """Pre-fill IRF if provided in URL"""
        initial = super().get_initial()
        irf_id = self.request.GET.get('irf')
        if irf_id:
            initial['irf'] = irf_id
        return initial

    def get_success_url(self):
        return reverse_lazy('irradiation:irf_detail', kwargs={'pk': self.object.irf.pk}) + '?tab=logs'


def home(request):
    """
    Home page with search bar and statistics
    """
    total_irfs = IrradiationRequestForm.objects.count()
    approved_irfs = IrradiationRequestForm.objects.filter(status='approved').count()
    total_logs = SampleIrradiationLog.objects.count()

    # Recent IRFs
    recent_irfs = IrradiationRequestForm.objects.all().order_by('-created_date')[:5]

    # Recent irradiations
    recent_logs = SampleIrradiationLog.objects.all().order_by('-irradiation_date')[:5]

    context = {
        'total_irfs': total_irfs,
        'approved_irfs': approved_irfs,
        'total_logs': total_logs,
        'recent_irfs': recent_irfs,
        'recent_logs': recent_logs,
    }

    return render(request, 'irradiation/home.html', context)
