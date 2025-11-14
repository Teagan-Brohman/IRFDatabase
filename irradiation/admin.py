from django.contrib import admin
from django.utils.html import format_html
from .models import (
    IrradiationRequestForm, SampleIrradiationLog, Sample, SampleComponent,
    FluxConfiguration, SampleComposition, ActivationResult
)


class SampleIrradiationLogInline(admin.TabularInline):
    """Inline admin for Sample Irradiation Logs"""
    model = SampleIrradiationLog
    extra = 1
    fields = [
        'irradiation_date', 'sample', 'sample_id_text', 'experimenter_name',
        'actual_location', 'actual_power', 'time_in', 'time_out',
        'total_time', 'total_time_unit', 'measured_dose_rate',
        'decay_time', 'decay_time_unit', 'operator_initials'
    ]
    classes = ['collapse']


@admin.register(IrradiationRequestForm)
class IrradiationRequestFormAdmin(admin.ModelAdmin):
    """Admin interface for Irradiation Request Forms"""

    list_display = [
        'irf_number',
        'sample_description_short',
        'status_badge',
        'max_power',
        'max_time',
        'max_mass',
        'total_irradiations',
        'created_date',
        'approval_status'
    ]

    list_filter = [
        'status',
        'physical_form',
        'encapsulation',
        'created_date',
        'approver1_role',
        'approver2_role',
    ]

    search_fields = [
        'irf_number',
        'sample_description',
        'requester_name',
        'experimenter_name',
    ]

    readonly_fields = ['created_date', 'updated_date']

    inlines = [SampleIrradiationLogInline]

    fieldsets = (
        ('IRF Identification', {
            'fields': (
                'irf_number',
                'status',
                ('created_date', 'updated_date'),
            )
        }),
        ('1. Irradiation Request - Sample Information', {
            'fields': (
                'sample_description',
                ('physical_form', 'physical_form_other'),
                ('encapsulation', 'encapsulation_other'),
                ('irradiation_location', 'irradiation_location_other'),
            ),
            'description': 'Section 1 - Completed by Experimenter'
        }),
        ('1. Irradiation Request - Limits', {
            'fields': (
                ('max_power', 'max_time', 'max_mass'),
            )
        }),
        ('1. Irradiation Request - Expected Dose Rate', {
            'fields': (
                'expected_dose_rate',
                'dose_rate_basis',
                'dose_rate_reference_irf',
                'dose_rate_calculation_notes',
            )
        }),
        ('1. Irradiation Request - Reactivity Worth', {
            'fields': (
                'reactivity_worth',
                'reactivity_basis',
                'reactivity_reference_irf',
            )
        }),
        ('1. Irradiation Request - Requester Info', {
            'fields': (
                'request_comments',
                'requester_name',
                'requester_signature_date',
            )
        }),
        ('2. Review and Approval - Hazard Analysis', {
            'fields': (
                ('reactivity_hazard', 'reactivity_hazard_notes'),
                ('dose_rate_hazard', 'dose_rate_hazard_notes'),
                ('reactor_equipment_hazard', 'reactor_equipment_hazard_notes'),
                ('other_hazard', 'other_hazard_notes'),
                'additional_restrictions',
            ),
            'description': 'Section 2 - Completed by Reviewers'
        }),
        ('2. Review and Approval - Approvals', {
            'fields': (
                ('approver1_role', 'approver1_name', 'approver1_date'),
                ('approver2_role', 'approver2_name', 'approver2_date'),
            ),
            'description': 'Two signatures required from Director, Manager, SRO, or Health Physicist'
        }),
    )

    def sample_description_short(self, obj):
        """Truncate sample description for list view"""
        return obj.sample_description[:60] + '...' if len(obj.sample_description) > 60 else obj.sample_description
    sample_description_short.short_description = 'Sample Description'

    def status_badge(self, obj):
        """Display status with color coding"""
        colors = {
            'draft': '#6c757d',
            'pending_review': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
            'archived': '#17a2b8',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def approval_status(self, obj):
        """Display approval status"""
        if obj.is_approved():
            return format_html('<span style="color: green;">✓ Approved</span>')
        else:
            return format_html('<span style="color: orange;">⚠ Pending</span>')
    approval_status.short_description = 'Approval'

    def get_queryset(self, request):
        """Optimize queryset with related logs"""
        qs = super().get_queryset(request)
        return qs.prefetch_related('irradiation_logs')

    class Media:
        css = {
            'all': ('admin/css/irradiation_admin.css',)
        }


@admin.register(SampleIrradiationLog)
class SampleIrradiationLogAdmin(admin.ModelAdmin):
    """Admin interface for individual Sample Irradiation Logs"""

    list_display = [
        'get_sample_id',
        'irf_link',
        'irradiation_date',
        'experimenter_name',
        'actual_location',
        'actual_power',
        'total_time',
        'measured_dose_rate',
        'within_limits_display',
    ]

    list_filter = [
        'irradiation_date',
        'actual_location',
        'experimenter_name',
    ]

    search_fields = [
        'sample_id_text',
        'sample__sample_id',
        'irf__irf_number',
        'experimenter_name',
    ]

    readonly_fields = ['created_date', 'updated_date', 'fluence', 'within_limits']

    fieldsets = (
        ('Associated IRF', {
            'fields': ('irf',)
        }),
        ('Sample Information', {
            'fields': (
                'irradiation_date',
                'sample',
                'sample_id_text',
                'experimenter_name',
            )
        }),
        ('Irradiation Details', {
            'fields': (
                'actual_location',
                'actual_power',
                ('time_in', 'time_out'),
                ('total_time', 'total_time_unit'),
            )
        }),
        ('Dose Measurements', {
            'fields': (
                'measured_dose_rate',
                ('decay_time', 'decay_time_unit'),
            )
        }),
        ('Operator & Notes', {
            'fields': (
                'operator_initials',
                'notes',
            )
        }),
        ('Calculated Fields & Metadata', {
            'fields': (
                'fluence',
                'within_limits',
                ('created_date', 'updated_date'),
            ),
            'classes': ('collapse',)
        }),
    )

    def irf_link(self, obj):
        """Create clickable link to parent IRF"""
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse('admin:irradiation_irradiationrequestform_change', args=[obj.irf.pk])
        return format_html('<a href="{}">{}</a>', url, obj.irf.irf_number)
    irf_link.short_description = 'IRF Number'

    def within_limits_display(self, obj):
        """Display whether irradiation is within IRF limits"""
        if obj.within_limits():
            return format_html('<span style="color: green;">✓ Within Limits</span>')
        else:
            return format_html('<span style="color: red;">⚠ Exceeds Limits</span>')
    within_limits_display.short_description = 'Limits Check'


# Sample Admin

class SampleComponentInline(admin.TabularInline):
    """Inline admin for Sample Components"""
    model = SampleComponent
    fk_name = 'combo_sample'
    extra = 1
    fields = ['component_sample', 'order']
    verbose_name = 'Component'
    verbose_name_plural = 'Components'


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    """Admin interface for Samples"""

    list_display = [
        'sample_id',
        'name',
        'material_type',
        'physical_form',
        'mass_display',
        'is_combo',
        'total_irradiations',
        'created_date',
    ]

    list_filter = [
        'is_combo',
        'physical_form',
        'material_type',
        'created_date',
    ]

    search_fields = [
        'sample_id',
        'name',
        'material_type',
        'description',
    ]

    readonly_fields = ['created_date', 'updated_date']

    fieldsets = (
        ('Sample Identification', {
            'fields': (
                'sample_id',
                'name',
                'is_combo',
                ('created_date', 'updated_date'),
            )
        }),
        ('Sample Properties', {
            'fields': (
                'material_type',
                'physical_form',
                ('mass', 'mass_unit'),
                'dimensions',
            )
        }),
        ('Description & Notes', {
            'fields': (
                'description',
                'notes',
            )
        }),
    )

    inlines = []

    def get_inlines(self, request, obj=None):
        """Show component inline only for combo samples"""
        if obj and obj.is_combo:
            return [SampleComponentInline]
        return []

    def mass_display(self, obj):
        """Display mass with unit"""
        if obj.mass:
            return f"{obj.mass} {obj.get_mass_unit_display()}"
        return "-"
    mass_display.short_description = 'Mass'


@admin.register(SampleComponent)
class SampleComponentAdmin(admin.ModelAdmin):
    """Admin interface for Sample Components"""

    list_display = [
        'combo_sample',
        'component_sample',
        'order',
    ]

    list_filter = [
        'combo_sample__is_combo',
    ]

    search_fields = [
        'combo_sample__sample_id',
        'component_sample__sample_id',
    ]


# Activation Analysis Admin

@admin.register(FluxConfiguration)
class FluxConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for Flux Configurations"""

    list_display = [
        'location',
        'thermal_flux_display',
        'fast_flux_display',
        'reference_power',
        'updated_date',
    ]

    list_filter = ['location']

    fieldsets = (
        ('Location', {
            'fields': ('location', 'reference_power')
        }),
        ('Neutron Flux Values', {
            'fields': (
                'thermal_flux',
                'fast_flux',
                'intermediate_flux',
                'cadmium_ratio',
            ),
            'description': 'Flux values at reference power (typically 200 kW)'
        }),
        ('Notes', {
            'fields': ('notes', 'updated_date'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['updated_date']

    def thermal_flux_display(self, obj):
        """Display thermal flux in scientific notation"""
        return f"{float(obj.thermal_flux):.2e} n/cm²/s"
    thermal_flux_display.short_description = 'Thermal Flux'

    def fast_flux_display(self, obj):
        """Display fast flux in scientific notation"""
        return f"{float(obj.fast_flux):.2e} n/cm²/s"
    fast_flux_display.short_description = 'Fast Flux'


class SampleCompositionInline(admin.TabularInline):
    """Inline admin for Sample Composition"""
    model = SampleComposition
    extra = 1
    fields = ['element', 'isotope', 'fraction', 'composition_type', 'order']
    verbose_name = 'Composition Element'
    verbose_name_plural = 'Elemental Composition'


# Update SampleAdmin to include composition inline
# Modify the existing SampleAdmin.inlines
SampleAdmin.inlines = [SampleCompositionInline]


@admin.register(ActivationResult)
class ActivationResultAdmin(admin.ModelAdmin):
    """Admin interface for Activation Results"""

    list_display = [
        'sample',
        'calculated_at',
        'total_activity_display',
        'number_of_isotopes',
        'calculation_method',
        'calculation_successful',
    ]

    list_filter = [
        'calculation_successful',
        'calculation_method',
        'calculated_at',
    ]

    search_fields = [
        'sample__sample_id',
        'notes',
    ]

    readonly_fields = [
        'calculated_at',
        'total_activity_bq',
        'total_activity_ci_display',
        'number_of_isotopes',
        'irradiation_hash',
    ]

    fieldsets = (
        ('Sample', {
            'fields': ('sample',)
        }),
        ('Calculation Info', {
            'fields': (
                'calculation_method',
                'calculated_at',
                'reference_time',
                'irradiation_hash',
            )
        }),
        ('Results', {
            'fields': (
                'total_activity_bq',
                'total_activity_ci_display',
                'estimated_dose_rate_1ft',
                'number_of_isotopes',
            )
        }),
        ('Status', {
            'fields': (
                'calculation_successful',
                'error_message',
            )
        }),
        ('Detailed Inventory', {
            'fields': ('isotopic_inventory', 'notes'),
            'classes': ('collapse',)
        }),
    )

    def total_activity_display(self, obj):
        """Display activity in scientific notation"""
        bq = float(obj.total_activity_bq)
        ci = bq / 3.7e10
        return f"{bq:.2e} Bq ({ci:.2e} Ci)"
    total_activity_display.short_description = 'Total Activity'

    def total_activity_ci_display(self, obj):
        """Display activity in Curies"""
        return f"{obj.get_activity_ci():.4e} Ci"
    total_activity_ci_display.short_description = 'Activity (Ci)'


# Customize admin site headers
admin.site.site_header = "IRF Database Administration"
admin.site.site_title = "IRF Database"
admin.site.index_title = "Welcome to the Irradiation Request Form Database"
