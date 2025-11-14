from django import forms
from django.forms import CheckboxSelectMultiple, inlineformset_factory
from .models import IrradiationRequestForm, SampleIrradiationLog, Sample, SampleComposition


class IRFForm(forms.ModelForm):
    """Custom form for IRF with enhanced widgets"""

    # Multiple selection for irradiation locations
    irradiation_locations = forms.MultipleChoiceField(
        choices=[
            ('bare_rabbit', 'Bare Rabbit'),
            ('cad_rabbit', 'Cad Rabbit'),
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

        # Conditional validation: Required fields enforced for approved/pending_review status
        status = cleaned_data.get('status')
        if status in ['approved', 'pending_review']:
            required_fields = {
                'irf_number': 'IRF Number',
                'sample_description': 'Sample Description',
                'physical_form': 'Physical Form',
                'encapsulation': 'Encapsulation',
                'max_power': 'Maximum Power',
                'max_time': 'Maximum Time',
                'max_mass': 'Maximum Mass',
                'expected_dose_rate': 'Expected Dose Rate',
                'dose_rate_basis': 'Dose Rate Basis',
                'reactivity_worth': 'Reactivity Worth',
                'reactivity_basis': 'Reactivity Basis',
                'requester_name': 'Requester Name',
            }

            for field, label in required_fields.items():
                if not cleaned_data.get(field):
                    self.add_error(field, f'{label} is required for {status.replace("_", " ")} IRFs.')

            # Location validation
            if not location_str:
                self.add_error(None, 'At least one irradiation location is required for approved/pending review IRFs.')

            # Approval validation for approved status
            if status == 'approved':
                if not cleaned_data.get('approver1_name') or not cleaned_data.get('approver1_date'):
                    self.add_error('approver1_name', 'First approver information is required for approved IRFs.')
                if not cleaned_data.get('approver2_name') or not cleaned_data.get('approver2_date'):
                    self.add_error('approver2_name', 'Second approver information is required for approved IRFs.')

        return cleaned_data


class SampleLogForm(forms.ModelForm):
    """Custom form for Sample Irradiation Log"""

    class Meta:
        model = SampleIrradiationLog
        fields = [
            'irf',
            'irradiation_date',
            'sample',
            'sample_id_text',
            'experimenter_name',
            'actual_location',
            'actual_power',
            'time_in',
            'time_out',
            'total_time',
            'total_time_unit',
            'measured_dose_rate',
            'decay_time',
            'decay_time_unit',
            'operator_initials',
            'notes',
        ]

        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'auto-grow'}),
            'irradiation_date': forms.DateInput(attrs={'type': 'date'}),
            'time_in': forms.TimeInput(attrs={'type': 'time'}),
            'time_out': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        # Extract irf_pk if provided
        irf_pk = kwargs.pop('irf_pk', None)
        super().__init__(*args, **kwargs)

        # If we have an IRF (either from instance or from irf_pk), populate location choices
        irf = None
        if self.instance.pk and self.instance.irf:
            irf = self.instance.irf
        elif irf_pk:
            try:
                irf = IrradiationRequestForm.objects.get(pk=irf_pk)
            except IrradiationRequestForm.DoesNotExist:
                pass

        if irf and irf.irradiation_location:
            # Parse the IRF's approved locations
            location_choices = []
            locations = [loc.strip() for loc in irf.irradiation_location.split(',')]

            # Map location codes to display names
            location_map = {
                'bare_rabbit': 'Bare Rabbit',
                'cad_rabbit': 'Cad Rabbit',
                'beam_port': 'Beam Port',
                'thermal_column': 'Thermal Column',
                'other': 'Other',
            }

            for loc in locations:
                if loc in location_map:
                    location_choices.append((loc, location_map[loc]))
                elif loc:  # For any other custom locations
                    location_choices.append((loc, loc.replace('_', ' ').title()))

            # Add custom location if specified
            if irf.irradiation_location_other:
                location_choices.append(('other_custom', f'Other: {irf.irradiation_location_other}'))

            if location_choices:
                self.fields['actual_location'] = forms.ChoiceField(
                    choices=location_choices,
                    required=True,
                    label='Location',
                    help_text='Select from IRF-approved locations'
                )

        # Make both sample fields optional in form (we'll validate in clean())
        self.fields['sample'].required = False
        self.fields['sample_id_text'].required = False

    def clean(self):
        """Validate that at least one sample identifier is provided"""
        cleaned_data = super().clean()
        sample = cleaned_data.get('sample')
        sample_id_text = cleaned_data.get('sample_id_text')

        # At least one must be provided
        if not sample and not sample_id_text:
            raise forms.ValidationError(
                'Either select a sample from the database or provide a sample ID in the text field.'
            )

        return cleaned_data


class SampleForm(forms.ModelForm):
    """Custom form for Sample with enhanced widgets"""

    class Meta:
        model = Sample
        fields = [
            'sample_id', 'name', 'description', 'material_type',
            'physical_form', 'mass', 'mass_unit', 'dimensions', 'notes'
        ]

        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class SampleCompositionForm(forms.ModelForm):
    """Form for individual composition elements"""

    class Meta:
        model = SampleComposition
        fields = ['element', 'isotope', 'fraction', 'composition_type', 'order']
        widgets = {
            'element': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Al, Cu, Au'}),
            'isotope': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Au-197 (optional)'}),
            'fraction': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'composition_type': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.HiddenInput(),
        }


# Formset for managing multiple composition elements
SampleCompositionFormSet = inlineformset_factory(
    Sample,
    SampleComposition,
    form=SampleCompositionForm,
    extra=0,  # Don't show extra forms by default, use "Add Element" button
    can_delete=True,
    min_num=0,
    validate_min=False,
)
