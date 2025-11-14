from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.db.models import Q, Count
from django.urls import reverse_lazy
from django.http import JsonResponse
from collections import OrderedDict
from .models import IrradiationRequestForm, SampleIrradiationLog
from .forms import IRFForm, SampleLogForm


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
        """Add sample logs and version history to context"""
        context = super().get_context_data(**kwargs)

        # Get all sample logs ordered by date (most recent first), then by time
        all_logs = self.object.irradiation_logs.all().order_by('-irradiation_date', '-time_in')

        # Group logs by date
        logs_by_date = OrderedDict()
        for log in all_logs:
            date_key = log.irradiation_date
            if date_key not in logs_by_date:
                logs_by_date[date_key] = []
            logs_by_date[date_key].append(log)

        context['sample_logs'] = all_logs  # Keep for backward compatibility
        context['logs_by_date'] = logs_by_date
        context['active_tab'] = self.request.GET.get('tab', 'details')

        # Add version history
        context['version_history'] = self.object.get_version_history()
        context['has_amendments'] = self.object.has_amendments()
        context['is_latest_version'] = self.object.is_latest_version()

        return context


class IRFCreateView(CreateView):
    """Create new IRF"""
    model = IrradiationRequestForm
    template_name = 'irradiation/irf_form.html'
    form_class = IRFForm
    success_url = reverse_lazy('irradiation:irf_list')


class IRFUpdateView(UpdateView):
    """Update existing IRF"""
    model = IrradiationRequestForm
    template_name = 'irradiation/irf_form.html'
    form_class = IRFForm

    def form_valid(self, form):
        """Handle amendment vs fix logic"""
        change_type = self.request.POST.get('change_type', 'fix')
        change_notes = self.request.POST.get('change_notes', '')

        if change_type == 'amendment':
            # Create a new version (amendment)
            old_irf = self.object
            new_irf = form.save(commit=False)
            new_irf.pk = None  # Create new object
            new_irf.parent_version = old_irf
            new_irf.version_number = old_irf.version_number + 1
            new_irf.change_type = 'amendment'
            new_irf.change_notes = change_notes
            new_irf.save()

            # Update the M2M relationships if any
            form.save_m2m()

            self.object = new_irf
            return super(UpdateView, self).form_valid(form)
        else:
            # Just a fix, update in place
            self.object.change_type = 'fix' if self.object.version_number > 1 else 'original'
            self.object.change_notes = change_notes
            return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('irradiation:irf_detail', kwargs={'pk': self.object.pk})


class SampleLogCreateView(CreateView):
    """Create new sample irradiation log"""
    model = SampleIrradiationLog
    template_name = 'irradiation/sample_log_form.html'
    form_class = SampleLogForm

    def get_initial(self):
        """Pre-fill IRF and date if provided in URL"""
        initial = super().get_initial()
        irf_id = self.request.GET.get('irf')
        if irf_id:
            initial['irf'] = irf_id

        # Pre-fill date if provided
        date = self.request.GET.get('date')
        if date:
            initial['irradiation_date'] = date

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


def irf_autocomplete(request):
    """
    API endpoint for IRF number autocomplete
    Returns matching IRF numbers and basic info
    """
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse({'results': []})

    irfs = IrradiationRequestForm.objects.filter(
        irf_number__icontains=query
    )[:10]

    results = [
        {
            'irf_number': irf.irf_number,
            'sample_description': irf.sample_description[:50],
            'status': irf.get_status_display(),
            'url': irf.get_absolute_url(),
        }
        for irf in irfs
    ]

    return JsonResponse({'results': results})
