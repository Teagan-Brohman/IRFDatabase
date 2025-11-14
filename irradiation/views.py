from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Q, Count, F
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from collections import OrderedDict
from .models import IrradiationRequestForm, SampleIrradiationLog, Sample, SampleComponent
from .forms import IRFForm, SampleLogForm, SampleForm, SampleCompositionFormSet


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
        """Filter IRFs based on search query - show only latest versions"""
        # Exclude IRFs that have been amended (i.e., have child amendments)
        # This ensures only the latest version of each IRF is shown
        queryset = IrradiationRequestForm.objects.filter(
            amendments__isnull=True  # No amendments means this is the latest version
        ).annotate(
            num_logs=Count('irradiation_logs', distinct=True)
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
            # Get a fresh copy of the original IRF from database BEFORE form modifies self.object
            old_irf = IrradiationRequestForm.objects.get(pk=self.object.pk)

            # Create a new version (amendment)
            new_irf = form.save(commit=False)
            new_irf.pk = None  # Create new object
            new_irf.parent_version = old_irf  # Now points to saved instance from DB
            new_irf.version_number = old_irf.version_number + 1
            new_irf.change_type = 'amendment'
            new_irf.change_notes = change_notes

            # Modify IRF number to include version suffix (e.g., "24-001" -> "24-001-v2")
            # This ensures uniqueness while keeping the base number for reference
            base_irf_number = old_irf.irf_number.split('-v')[0]  # Strip existing version suffix if any
            new_irf.irf_number = f"{base_irf_number}-v{new_irf.version_number}"

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

    def get_form_kwargs(self):
        """Pass irf_pk to form for location choices"""
        kwargs = super().get_form_kwargs()
        irf_id = self.request.GET.get('irf')
        if irf_id:
            kwargs['irf_pk'] = irf_id
        return kwargs

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

    def get_context_data(self, **kwargs):
        """Add IRF to context for cancel button"""
        context = super().get_context_data(**kwargs)
        irf_id = self.request.GET.get('irf')
        if irf_id:
            try:
                context['irf'] = IrradiationRequestForm.objects.get(pk=irf_id)
            except IrradiationRequestForm.DoesNotExist:
                pass
        return context

    def get_success_url(self):
        """Return to sample logs tab with the date's accordion expanded"""
        date_param = self.object.irradiation_date.strftime('%Y%m%d')
        return reverse_lazy('irradiation:irf_detail', kwargs={'pk': self.object.irf.pk}) + f'?tab=logs#collapse{date_param}'


class SampleLogUpdateView(UpdateView):
    """Update existing sample irradiation log"""
    model = SampleIrradiationLog
    template_name = 'irradiation/sample_log_form.html'
    form_class = SampleLogForm

    def get_form_kwargs(self):
        """Pass irf_pk to form for location choices"""
        kwargs = super().get_form_kwargs()
        if self.object.irf:
            kwargs['irf_pk'] = self.object.irf.pk
        return kwargs

    def get_context_data(self, **kwargs):
        """Add IRF to context for cancel button"""
        context = super().get_context_data(**kwargs)
        if self.object.irf:
            context['irf'] = self.object.irf
        return context

    def get_success_url(self):
        """Return to sample logs tab with the date's accordion expanded"""
        date_param = self.object.irradiation_date.strftime('%Y%m%d')
        return reverse_lazy('irradiation:irf_detail', kwargs={'pk': self.object.irf.pk}) + f'?tab=logs#collapse{date_param}'


class SampleLogDeleteView(DeleteView):
    """Delete sample irradiation log"""
    model = SampleIrradiationLog
    template_name = 'irradiation/sample_log_confirm_delete.html'

    def get_context_data(self, **kwargs):
        """Add IRF to context"""
        context = super().get_context_data(**kwargs)
        if self.object.irf:
            context['irf'] = self.object.irf
        return context

    def get_success_url(self):
        """Return to sample logs tab"""
        return reverse_lazy('irradiation:irf_detail', kwargs={'pk': self.object.irf.pk}) + '?tab=logs'


def home(request):
    """
    Home page with search bar and statistics
    """
    # Only count latest versions (IRFs without amendments)
    latest_irfs = IrradiationRequestForm.objects.filter(amendments__isnull=True)
    total_irfs = latest_irfs.count()
    approved_irfs = latest_irfs.filter(status='approved').count()
    total_logs = SampleIrradiationLog.objects.count()

    # Recent IRFs (latest versions only)
    recent_irfs = latest_irfs.order_by('-created_date')[:5]

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
    Returns matching IRF numbers and basic info (latest versions only)
    """
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse({'results': []})

    # Only return latest versions (IRFs without amendments)
    irfs = IrradiationRequestForm.objects.filter(
        irf_number__icontains=query,
        amendments__isnull=True
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


# ========================================
# SAMPLE VIEWS
# ========================================

class SampleListView(ListView):
    """List view for base samples (non-combo)"""
    model = Sample
    template_name = 'irradiation/sample_list.html'
    context_object_name = 'samples'
    paginate_by = 50

    def get_queryset(self):
        """Filter to show only base samples"""
        queryset = Sample.objects.filter(is_combo=False).annotate(
            direct_irradiations=Count('irradiation_logs', distinct=True),
            combo_irradiations=Count('used_in_combos__combo_sample__irradiation_logs', distinct=True),
            num_irradiations=F('direct_irradiations') + F('combo_irradiations')
        )

        # Search functionality
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(sample_id__icontains=query) |
                Q(name__icontains=query) |
                Q(material_type__icontains=query) |
                Q(description__icontains=query)
            )

        # Material type filter
        material = self.request.GET.get('material', '')
        if material:
            queryset = queryset.filter(material_type__icontains=material)

        # Physical form filter
        physical_form = self.request.GET.get('physical_form', '')
        if physical_form:
            queryset = queryset.filter(physical_form=physical_form)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['selected_material'] = self.request.GET.get('material', '')
        context['selected_physical_form'] = self.request.GET.get('physical_form', '')
        context['physical_form_choices'] = Sample.PHYSICAL_FORM_CHOICES

        # Get unique material types for filter
        context['available_materials'] = Sample.objects.filter(is_combo=False).exclude(
            material_type=''
        ).values_list('material_type', flat=True).distinct().order_by('material_type')

        return context


class ComboSampleListView(ListView):
    """List view for combo samples"""
    model = Sample
    template_name = 'irradiation/combo_sample_list.html'
    context_object_name = 'samples'
    paginate_by = 50

    def get_queryset(self):
        """Filter to show only combo samples"""
        queryset = Sample.objects.filter(is_combo=True).annotate(
            num_irradiations=Count('irradiation_logs', distinct=True),
            num_components=Count('combo_components', distinct=True)
        )

        # Search functionality
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(sample_id__icontains=query) |
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class SampleDetailView(DetailView):
    """Detail view for a sample showing irradiation history"""
    model = Sample
    template_name = 'irradiation/sample_detail.html'
    context_object_name = 'sample'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all irradiation logs for this sample
        logs = self.object.get_irradiation_logs().order_by('-irradiation_date', '-time_in')
        context['irradiation_logs'] = logs

        # If combo, get components
        if self.object.is_combo:
            context['components'] = self.object.get_components()

        # If base sample, get combos this sample is part of
        if not self.object.is_combo:
            context['used_in_combos'] = Sample.objects.filter(
                combo_components__component_sample=self.object
            ).distinct()

        return context


class SampleCreateView(CreateView):
    """Create a new base sample"""
    model = Sample
    template_name = 'irradiation/sample_form.html'
    form_class = SampleForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['composition_formset'] = SampleCompositionFormSet(self.request.POST, instance=self.object)
        else:
            context['composition_formset'] = SampleCompositionFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        composition_formset = context['composition_formset']

        # Ensure is_combo is False for base samples
        form.instance.is_combo = False

        # Validate formset
        if composition_formset.is_valid():
            self.object = form.save()
            composition_formset.instance = self.object
            composition_formset.save()

            # Handle AJAX requests (from quick add modal)
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
               self.request.content_type == 'application/x-www-form-urlencoded':
                return JsonResponse({
                    'success': True,
                    'sample_id': self.object.sample_id,
                    'sample_pk': self.object.pk,
                    'url': self.object.get_absolute_url()
                })

            messages.success(self.request, f'Sample {form.instance.sample_id} created successfully.')
            return redirect(self.object.get_absolute_url())
        else:
            return self.form_invalid(form)

    def form_invalid(self, form):
        # Handle AJAX requests
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
           self.request.content_type == 'application/x-www-form-urlencoded':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
        return super().form_invalid(form)


class SampleUpdateView(UpdateView):
    """Update an existing sample"""
    model = Sample
    template_name = 'irradiation/sample_form.html'
    form_class = SampleForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['composition_formset'] = SampleCompositionFormSet(self.request.POST, instance=self.object)
        else:
            context['composition_formset'] = SampleCompositionFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        composition_formset = context['composition_formset']

        # Validate formset
        if composition_formset.is_valid():
            self.object = form.save()
            composition_formset.instance = self.object
            composition_formset.save()

            messages.success(self.request, f'Sample {form.instance.sample_id} updated successfully.')
            return redirect(self.object.get_absolute_url())
        else:
            return self.form_invalid(form)


class ComboSampleCreateView(CreateView):
    """Create a new combo sample with component selection and duplicate detection"""
    model = Sample
    template_name = 'irradiation/combo_sample_form.html'
    fields = ['sample_id', 'name', 'description', 'notes']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get all base samples for component selection
        context['base_samples'] = Sample.objects.filter(is_combo=False).order_by('sample_id')
        return context

    def form_valid(self, form):
        # Get selected component IDs from POST
        component_ids = self.request.POST.getlist('components')

        if not component_ids:
            messages.error(self.request, 'Please select at least one component sample.')
            return self.form_invalid(form)

        # Check for duplicate combo (same set of components)
        duplicate = self._find_duplicate_combo(component_ids)
        if duplicate:
            messages.warning(
                self.request,
                f'A combo with these exact components already exists: {duplicate.sample_id}'
            )
            return redirect('irradiation:sample_detail', pk=duplicate.pk)

        # Create the combo sample
        form.instance.is_combo = True
        response = super().form_valid(form)

        # Add components
        for order, component_id in enumerate(component_ids):
            component = Sample.objects.get(pk=component_id)
            SampleComponent.objects.create(
                combo_sample=self.object,
                component_sample=component,
                order=order
            )

        messages.success(
            self.request,
            f'Combo sample {self.object.sample_id} created with {len(component_ids)} components.'
        )
        return response

    def _find_duplicate_combo(self, component_ids):
        """Find existing combo with exact same set of components"""
        component_ids = set(map(int, component_ids))

        # Get all combo samples
        for combo in Sample.objects.filter(is_combo=True):
            existing_ids = set(combo.combo_components.values_list('component_sample_id', flat=True))
            if existing_ids == component_ids:
                return combo
        return None


def sample_autocomplete(request):
    """
    API endpoint for sample ID autocomplete
    Returns matching samples with basic info
    """
    query = request.GET.get('q', '').strip().upper()

    if len(query) < 1:
        return JsonResponse({'results': []})

    samples = Sample.objects.filter(
        sample_id__icontains=query
    )[:10]

    results = [
        {
            'sample_id': sample.sample_id,
            'name': sample.name,
            'material_type': sample.material_type,
            'is_combo': sample.is_combo,
            'num_components': sample.combo_components.count() if sample.is_combo else 0,
            'components': [c.sample_id for c in sample.get_components()] if sample.is_combo else [],
            'url': sample.get_absolute_url(),
        }
        for sample in samples
    ]

    return JsonResponse({'results': results})


# ========================================
# ACTIVATION ANALYSIS VIEWS
# ========================================

def calculate_sample_isotopics(request, pk):
    """
    Calculate isotopic inventory for a sample based on irradiation history

    Args:
        request: HTTP request
        pk: Sample primary key

    Returns:
        JsonResponse with calculation results
    """
    from .models import FluxConfiguration, ActivationResult
    from .activation import ActivationCalculator
    from datetime import datetime
    import logging

    logger = logging.getLogger(__name__)

    try:
        sample = get_object_or_404(Sample, pk=pk)

        # Get all irradiation logs for this sample (chronological order)
        logs = sample.get_irradiation_logs().order_by('irradiation_date', 'time_in')

        if not logs.exists():
            return JsonResponse({
                'success': False,
                'error': 'No irradiation history found for this sample.'
            }, status=400)

        # Get flux configurations
        flux_configs = {}
        for config in FluxConfiguration.objects.all():
            flux_configs[config.location] = config

        if not flux_configs:
            return JsonResponse({
                'success': False,
                'error': 'No flux configurations found. Please configure flux values in Admin.'
            }, status=400)

        # Get calculation parameters from request
        use_multigroup = request.GET.get('multigroup', 'true').lower() == 'true'
        min_fraction = float(request.GET.get('min_fraction', '0.001'))
        use_cache = request.GET.get('use_cache', 'true').lower() == 'true'

        # Initialize calculator
        calculator = ActivationCalculator(use_multigroup=use_multigroup)

        # Perform calculation
        results = calculator.calculate_activation(
            sample=sample,
            irradiation_logs=logs,
            flux_configs=flux_configs,
            min_activity_fraction=min_fraction,
            use_cache=use_cache
        )

        if not results.get('calculation_successful', False):
            return JsonResponse({
                'success': False,
                'error': results.get('error_message', 'Calculation failed')
            }, status=500)

        # Save results to database (cache for future use)
        if not results.get('from_cache', False):
            _save_activation_result(sample, results, use_multigroup)

        # Prepare response
        skipped = results.get('skipped_irradiations', [])
        response_data = {
            'success': True,
            'sample_id': sample.sample_id,
            'total_activity_bq': results['total_activity_bq'],
            'total_activity_ci': results['total_activity_bq'] / 3.7e10,
            'reference_time': results['reference_time'],
            'isotopes': results['isotopes'],
            'estimated_dose_rate_1ft': results.get('estimated_dose_rate_1ft'),
            'num_isotopes': len(results['isotopes']),
            'from_cache': results.get('from_cache', False),
            'irradiation_count': logs.count(),
            'skipped_irradiations': skipped,
            'processed_count': logs.count() - len(skipped),
        }

        return JsonResponse(response_data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def _save_activation_result(sample, results, use_multigroup):
    """Helper function to save activation results to database"""
    from .models import ActivationResult
    from datetime import datetime
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Parse reference time
        ref_time = datetime.fromisoformat(results['reference_time'])

        # Create or update result
        result, created = ActivationResult.objects.update_or_create(
            sample=sample,
            irradiation_hash=results['irradiation_hash'],
            defaults={
                'reference_time': ref_time,
                'total_activity_bq': results['total_activity_bq'],
                'estimated_dose_rate_1ft': results.get('estimated_dose_rate_1ft'),
                'isotopic_inventory': results['isotopes'],
                'calculation_method': 'multi-group' if use_multigroup else 'one-group',
                'number_of_isotopes': len(results['isotopes']),
                'calculation_successful': True,
                'error_message': '',
            }
        )

        if created:
            logger.info(f"Saved new activation result for {sample.sample_id}")
        else:
            logger.info(f"Updated activation result for {sample.sample_id}")

    except Exception as e:
        logger.error(f"Failed to save activation result: {e}")
