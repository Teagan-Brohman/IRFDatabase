from django import forms
from django.forms import CheckboxSelectMultiple
from .models import IrradiationRequestForm, SampleIrradiationLog


class IRFForm(forms.ModelForm):
    """Custom form for IRF with enhanced widgets"""

    # Multiple selection for irradiation locations
    irradiation_locations = forms.MultipleChoiceField(
        choices=[
            ('bare_rabbit_tube', 'Bare Rabbit Tube'),
            ('cadmium_rabbit_tube', 'Cadmium Rabbit Tube'),
            ('beam_port', 'Beam Port'),
            ('thermal_column', 'Thermal Column'),
        ],
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Irradiation Location(s)',
        help_text='Select one or more irradiation facilities'
    )

    location_other = forms.BooleanField(
        required=False,
        label='Other Location',
        help_text='Check if location is not listed above'
    )

    class Meta:
        model = IrradiationRequestForm
        fields = [
            # Section 1: Irradiation Request
            'irf_number',
            'sample_description',
            'physical_form',
            'physical_form_other',
            'encapsulation',
            'encapsulation_other',
            # Location handled separately
            'irradiation_location_other',
            'max_power',
            'max_power_unit',
            'max_time',
            'max_time_unit',
            'max_mass',
            'max_mass_unit',
            'expected_dose_rate',
            'dose_rate_basis',
            'dose_rate_reference_irf',
            'dose_rate_calculation_notes',
            'reactivity_worth',
            'reactivity_basis',
            'reactivity_reference_irf',
            'sop306_calculation_file',
            'request_comments',
            'requester_name',
            'requester_signature_date',
            # Section 2: Review and Approval (usually completed separately)
            'status',
            'reactivity_hazard',
            'reactivity_hazard_notes',
            'dose_rate_hazard',
            'dose_rate_hazard_notes',
            'reactor_equipment_hazard',
            'reactor_equipment_hazard_notes',
            'other_hazard',
            'other_hazard_notes',
            'additional_restrictions',
            'approver1_role',
            'approver1_name',
            'approver1_date',
            'approver2_role',
            'approver2_name',
            'approver2_date',
        ]

        widgets = {
            'sample_description': forms.Textarea(attrs={'rows': 3, 'class': 'auto-grow'}),
            'dose_rate_calculation_notes': forms.Textarea(attrs={'rows': 3, 'class': 'auto-grow'}),
            'request_comments': forms.Textarea(attrs={'rows': 3, 'class': 'auto-grow'}),
            'reactivity_hazard_notes': forms.Textarea(attrs={'rows': 2, 'class': 'auto-grow'}),
            'dose_rate_hazard_notes': forms.Textarea(attrs={'rows': 2, 'class': 'auto-grow'}),
            'reactor_equipment_hazard_notes': forms.Textarea(attrs={'rows': 2, 'class': 'auto-grow'}),
            'other_hazard_notes': forms.Textarea(attrs={'rows': 2, 'class': 'auto-grow'}),
            'additional_restrictions': forms.Textarea(attrs={'rows': 3, 'class': 'auto-grow'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pre-populate location checkboxes if editing existing IRF
        if self.instance.pk and self.instance.irradiation_location:
            locations = self.instance.irradiation_location.split(',')
            self.initial['irradiation_locations'] = [loc.strip() for loc in locations if loc.strip() in dict(self.fields['irradiation_locations'].choices)]
            if self.instance.irradiation_location_other:
                self.initial['location_other'] = True

    def clean(self):
        cleaned_data = super().clean()

        # Combine selected locations into comma-separated string
        selected_locations = cleaned_data.get('irradiation_locations', [])
        location_other = cleaned_data.get('location_other', False)

        if selected_locations:
            location_str = ', '.join(selected_locations)
            if location_other:
                location_str += ', other'
        elif location_other:
            location_str = 'other'
        else:
            location_str = ''

        self.instance.irradiation_location = location_str

        return cleaned_data


class SampleLogForm(forms.ModelForm):
    """Custom form for Sample Irradiation Log"""

    class Meta:
        model = SampleIrradiationLog
        fields = [
            'irf',
            'irradiation_date',
            'sample_id',
            'experimenter_name',
            'actual_location',
            'actual_power',
            'time_in',
            'time_out',
            'total_time',
            'measured_dose_rate',
            'decay_time',
            'operator_initials',
            'notes',
        ]

        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'auto-grow'}),
            'irradiation_date': forms.DateInput(attrs={'type': 'date'}),
            'time_in': forms.TimeInput(attrs={'type': 'time'}),
            'time_out': forms.TimeInput(attrs={'type': 'time'}),
        }
