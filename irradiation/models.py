from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse


# Shared location choices for consistency across all models
LOCATION_CHOICES = [
    ('bare_rabbit', 'Bare Rabbit'),
    ('cad_rabbit', 'Cad Rabbit'),
    ('beam_port', 'Beam Port'),
    ('thermal_column', 'Thermal Column'),
    ('other', 'Other'),
]


class IrradiationRequestForm(models.Model):
    """
    Main IRF model based on Missouri S&T SOP 702
    One IRF can have multiple sample irradiations
    """

    # IRF Identification
    irf_number = models.CharField(
        max_length=20,
        help_text="Sequential number following last two digits of year (e.g. 95-1, 95-2)"
    )
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now=True)

    # Version/Amendment Tracking
    version_number = models.IntegerField(
        default=1,
        help_text="Version number for this IRF (1, 2, 3, etc.)"
    )
    parent_version = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='amendments',
        help_text="Previous version if this is an amendment"
    )
    CHANGE_TYPE_CHOICES = [
        ('original', 'Original'),
        ('fix', 'Minor Fix/Correction'),
        ('amendment', 'Amendment'),
    ]
    change_type = models.CharField(
        max_length=20,
        choices=CHANGE_TYPE_CHOICES,
        default='original',
        help_text="Type of change from previous version"
    )
    change_notes = models.TextField(
        blank=True,
        help_text="Notes about what changed in this version"
    )

    # 1. IRRADIATION REQUEST SECTION (Completed by Experimenter)

    # a. Sample Description
    sample_description = models.TextField(
        help_text="Describe the sample material (e.g. dried tobacco leaves, powdered milk, gold foil)"
    )

    # b. Physical Form
    PHYSICAL_FORM_CHOICES = [
        ('powder', 'Powder'),
        ('ash', 'Ash'),
        ('liquid', 'Liquid'),
        ('solid', 'Solid'),
        ('foil', 'Foil'),
        ('pellet', 'Pellet'),
        ('wire', 'Wire'),
        ('other', 'Other'),
    ]
    physical_form = models.CharField(
        max_length=50,
        choices=PHYSICAL_FORM_CHOICES,
        default='other'
    )
    physical_form_other = models.CharField(
        max_length=100,
        blank=True,
        help_text="Specify if 'Other' selected"
    )

    # c. Encapsulation
    ENCAPSULATION_CHOICES = [
        ('poly_vial', 'Poly-Vial'),
        ('other', 'Other'),
    ]
    encapsulation = models.CharField(
        max_length=50,
        choices=ENCAPSULATION_CHOICES,
        default='poly_vial'
    )
    encapsulation_other = models.CharField(
        max_length=200,
        blank=True,
        help_text="Describe if 'Other' selected"
    )

    # d. Irradiation Location
    # Allow multiple locations (stored as comma-separated or use ManyToMany in future)
    irradiation_location = models.CharField(
        max_length=200,
        choices=LOCATION_CHOICES,
        help_text="Select irradiation facility. Multiple may be authorized on single IRF"
    )
    irradiation_location_other = models.CharField(
        max_length=200,
        blank=True,
        help_text="Describe location (e.g. 'wire stringer in Grid Position C-3')"
    )

    # e. Irradiation Limits
    POWER_UNIT_CHOICES = [
        ('kw', 'kW (kilowatts)'),
        ('mw', 'mW (milliwatts)'),
        ('w', 'W (watts)'),
    ]
    max_power = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Maximum reactor power for irradiation"
    )
    max_power_unit = models.CharField(
        max_length=10,
        choices=POWER_UNIT_CHOICES,
        default='kw'
    )

    TIME_UNIT_CHOICES = [
        ('min', 'minutes'),
        ('hr', 'hours'),
        ('sec', 'seconds'),
    ]
    max_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Irradiation time at maximum power"
    )
    max_time_unit = models.CharField(
        max_length=10,
        choices=TIME_UNIT_CHOICES,
        default='min'
    )

    MASS_UNIT_CHOICES = [
        ('g', 'grams (g)'),
        ('kg', 'kilograms (kg)'),
        ('mg', 'milligrams (mg)'),
    ]
    max_mass = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(0)],
        help_text="Maximum sample mass to be irradiated in single irradiation"
    )
    max_mass_unit = models.CharField(
        max_length=10,
        choices=MASS_UNIT_CHOICES,
        default='g'
    )

    # f. Expected Dose Rate
    expected_dose_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Expected 1 foot dose rate (mrem/hr) when sample exits reactor"
    )

    DOSE_RATE_BASIS_CHOICES = [
        ('experience', 'Experience'),
        ('calculations', 'Calculations'),
        ('unknown', 'Completely Unknown'),
    ]
    dose_rate_basis = models.CharField(
        max_length=20,
        choices=DOSE_RATE_BASIS_CHOICES,
        default='experience'
    )
    dose_rate_reference_irf = models.CharField(
        max_length=20,
        blank=True,
        help_text="Reference IRF number if based on experience"
    )
    dose_rate_calculation_notes = models.TextField(
        blank=True,
        help_text="Calculation method and details if applicable"
    )

    # g. Reactivity Worth
    reactivity_worth = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        validators=[MinValueValidator(0), MaxValueValidator(1.2)],
        help_text="Expected reactivity worth (% Δk/k). Total of all experiments limited to 1.2%"
    )

    REACTIVITY_BASIS_CHOICES = [
        ('default', 'Default'),
        ('experience', 'Experience'),
        ('sop306', 'SOP 306 Calculations'),
        ('unknown', 'Completely Unknown'),
    ]
    reactivity_basis = models.CharField(
        max_length=20,
        choices=REACTIVITY_BASIS_CHOICES,
        default='default'
    )
    reactivity_reference_irf = models.CharField(
        max_length=20,
        blank=True,
        help_text="Reference IRF number if based on experience"
    )
    sop306_calculation_file = models.FileField(
        upload_to='sop306_calculations/',
        blank=True,
        null=True,
        help_text="Upload SOP 306 calculation file (PDF, Excel, etc.)"
    )

    # h. Comments
    request_comments = models.TextField(
        blank=True,
        help_text="Additional comments from requester"
    )

    # i. Request Completed By
    requester_name = models.CharField(
        max_length=200,
        help_text="Person completing the irradiation request"
    )
    requester_signature_date = models.DateField(
        null=True,
        blank=True
    )

    # 2. REVIEW AND APPROVAL SECTION

    # a. Analysis of Potential Hazards

    # 1) Reactivity
    HAZARD_CHOICES = [
        ('none', 'None'),
        ('other', 'Other'),
    ]
    reactivity_hazard = models.CharField(
        max_length=10,
        choices=HAZARD_CHOICES,
        default='none'
    )
    reactivity_hazard_notes = models.TextField(blank=True)

    # 2) Dose Rate
    dose_rate_hazard = models.CharField(
        max_length=10,
        choices=HAZARD_CHOICES,
        default='none'
    )
    dose_rate_hazard_notes = models.TextField(blank=True)

    # 3) Reactor Equipment
    reactor_equipment_hazard = models.CharField(
        max_length=10,
        choices=HAZARD_CHOICES,
        default='none'
    )
    reactor_equipment_hazard_notes = models.TextField(blank=True)

    # 4) Other Hazards
    other_hazard = models.CharField(
        max_length=10,
        choices=HAZARD_CHOICES,
        default='none'
    )
    other_hazard_notes = models.TextField(blank=True)

    # b. Additional Restrictions/Requirements
    additional_restrictions = models.TextField(
        blank=True,
        help_text="Additional restrictions or requirements from reviewers"
    )

    # c. Approvals (Two signatures required)
    # First Approver
    APPROVER_ROLE_CHOICES = [
        ('director', 'Director'),
        ('manager', 'Manager'),
        ('sro', 'SRO'),
        ('health_physicist', 'Health Physicist'),
    ]

    approver1_role = models.CharField(
        max_length=20,
        choices=APPROVER_ROLE_CHOICES,
        blank=True
    )
    approver1_name = models.CharField(max_length=200, blank=True)
    approver1_date = models.DateField(null=True, blank=True)

    # Second Approver
    approver2_role = models.CharField(
        max_length=20,
        choices=APPROVER_ROLE_CHOICES,
        blank=True
    )
    approver2_name = models.CharField(max_length=200, blank=True)
    approver2_date = models.DateField(null=True, blank=True)

    # Status tracking
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_review', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('archived', 'Archived'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    class Meta:
        ordering = ['-irf_number', '-version_number']
        verbose_name = 'Irradiation Request Form'
        verbose_name_plural = 'Irradiation Request Forms'
        unique_together = [['irf_number', 'version_number']]

    def __str__(self):
        version_str = f" (v{self.version_number})" if self.version_number > 1 else ""
        return f"IRF {self.irf_number}{version_str} - {self.sample_description[:50]}"

    def get_absolute_url(self):
        return reverse('irradiation:irf_detail', kwargs={'pk': self.pk})

    def is_approved(self):
        """Check if IRF has two approvals"""
        return bool(self.approver1_date and self.approver2_date)

    def total_irradiations(self):
        """Count total irradiations performed under this IRF (including all versions)"""
        return self.get_all_irradiation_logs().count()

    def has_amendments(self):
        """Check if this IRF has any amendments"""
        return self.amendments.exists()

    def get_version_history(self):
        """Get all versions of this IRF in chronological order"""
        # Start with this version
        current = self
        # Go back to find the original
        while current.parent_version:
            current = current.parent_version
        # Now get all amendments forward from original
        versions = [current]
        self._collect_amendments(current, versions)
        return versions

    def _collect_amendments(self, irf, versions):
        """Recursively collect all amendments"""
        for amendment in irf.amendments.all().order_by('created_date'):
            versions.append(amendment)
            self._collect_amendments(amendment, versions)

    def get_latest_version(self):
        """Get the latest version in the amendment chain"""
        versions = self.get_version_history()
        return versions[-1] if versions else self

    def is_latest_version(self):
        """Check if this is the latest version"""
        return not self.has_amendments()

    def get_all_irradiation_logs(self):
        """
        Get all irradiation logs from this IRF and all its version history
        This ensures that amended IRFs show logs from previous versions too
        """
        # Get all versions in the history
        versions = self.get_version_history()

        # Get all PKs of versions
        version_pks = [v.pk for v in versions]

        # Return all logs from all versions (no duplicates since each log has one IRF)
        return SampleIrradiationLog.objects.filter(
            irf__pk__in=version_pks
        ).distinct()


class Sample(models.Model):
    """
    Represents an individual sample that can be irradiated
    Samples can be base samples (e.g., aluminum foil, copper wire)
    or combo samples (combinations of multiple base samples)
    """

    # Sample Identification (case-insensitive)
    sample_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique sample identifier (case-insensitive)"
    )

    # Basic Information
    name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Descriptive name for the sample"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the sample"
    )

    # Sample Properties
    material_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Material composition (e.g., Aluminum, Copper, Gold, etc.)"
    )

    PHYSICAL_FORM_CHOICES = [
        ('powder', 'Powder'),
        ('ash', 'Ash'),
        ('liquid', 'Liquid'),
        ('solid', 'Solid'),
        ('foil', 'Foil'),
        ('pellet', 'Pellet'),
        ('wire', 'Wire'),
        ('other', 'Other'),
    ]
    physical_form = models.CharField(
        max_length=50,
        choices=PHYSICAL_FORM_CHOICES,
        blank=True,
        help_text="Physical form of the sample"
    )

    # Measurements
    MASS_UNIT_CHOICES = [
        ('g', 'grams (g)'),
        ('kg', 'kilograms (kg)'),
        ('mg', 'milligrams (mg)'),
    ]
    mass = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Sample mass"
    )
    mass_unit = models.CharField(
        max_length=10,
        choices=MASS_UNIT_CHOICES,
        default='g',
        blank=True
    )

    dimensions = models.CharField(
        max_length=200,
        blank=True,
        help_text="Physical dimensions (e.g., '2cm x 3cm x 0.1mm')"
    )

    # Sample Type
    is_combo = models.BooleanField(
        default=False,
        help_text="True if this is a combination of multiple base samples"
    )

    # Tracking
    created_date = models.DateField(
        auto_now_add=True,
        help_text="Date sample was added to database"
    )
    updated_date = models.DateField(auto_now=True)

    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this sample"
    )

    class Meta:
        ordering = ['sample_id']
        verbose_name = 'Sample'
        verbose_name_plural = 'Samples'

    def __str__(self):
        if self.name:
            return f"{self.sample_id} - {self.name}"
        return self.sample_id

    def save(self, *args, **kwargs):
        """Ensure sample_id is stored in uppercase for case-insensitive uniqueness"""
        self.sample_id = self.sample_id.upper()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('irradiation:sample_detail', kwargs={'pk': self.pk})

    def get_components(self):
        """Get list of component samples if this is a combo"""
        if not self.is_combo:
            return []
        return [sc.component_sample for sc in self.combo_components.all().order_by('order')]

    def get_irradiation_logs(self):
        """Get all irradiation logs for this sample (direct or as part of combo)"""
        # Direct irradiations
        direct_logs = self.irradiation_logs.all()

        # If this is a base sample, also get logs where it was part of a combo
        if not self.is_combo:
            combo_logs = SampleIrradiationLog.objects.filter(
                sample__combo_components__component_sample=self
            ).distinct()
            # Combine querysets
            from django.db.models import Q
            all_log_ids = list(direct_logs.values_list('id', flat=True)) + \
                         list(combo_logs.values_list('id', flat=True))
            return SampleIrradiationLog.objects.filter(id__in=all_log_ids).distinct()

        return direct_logs

    def total_irradiations(self):
        """Count total irradiations this sample has been through"""
        return self.get_irradiation_logs().count()


class SampleComponent(models.Model):
    """
    Through model linking combo samples to their component base samples
    Allows tracking which base samples make up a combo sample
    """

    combo_sample = models.ForeignKey(
        Sample,
        on_delete=models.CASCADE,
        related_name='combo_components',
        limit_choices_to={'is_combo': True},
        help_text="The combo sample"
    )

    component_sample = models.ForeignKey(
        Sample,
        on_delete=models.CASCADE,
        related_name='used_in_combos',
        limit_choices_to={'is_combo': False},
        help_text="A base sample that is part of this combo"
    )

    order = models.IntegerField(
        default=0,
        help_text="Order of this component in the combo (for display purposes)"
    )

    class Meta:
        ordering = ['combo_sample', 'order']
        verbose_name = 'Sample Component'
        verbose_name_plural = 'Sample Components'
        unique_together = ['combo_sample', 'component_sample']

    def __str__(self):
        return f"{self.combo_sample.sample_id} contains {self.component_sample.sample_id}"


class SampleIrradiationLog(models.Model):
    """
    Individual sample irradiation log entry
    Multiple logs can be associated with one IRF
    Based on Section D of SOP 702
    """

    # Link to parent IRF
    irf = models.ForeignKey(
        IrradiationRequestForm,
        on_delete=models.CASCADE,
        related_name='irradiation_logs',
        help_text="Associated Irradiation Request Form"
    )

    # Link to Sample (optional, for new entries)
    sample = models.ForeignKey(
        Sample,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='irradiation_logs',
        help_text="Link to sample in database (optional, for tracking)"
    )

    # 1. Date
    irradiation_date = models.DateField(
        help_text="Date of sample irradiation"
    )

    # 2. Sample ID (text field for backward compatibility with historical data)
    sample_id_text = models.CharField(
        max_length=100,
        help_text="Sample identification number or name (text-based, for historical records)"
    )

    # 3. Experimenter's Name
    experimenter_name = models.CharField(
        max_length=200,
        help_text="Name of experimenter responsible for the sample"
    )

    # 4. Location
    actual_location = models.CharField(
        max_length=200,
        choices=LOCATION_CHOICES,
        help_text="Actual irradiation location used"
    )

    # 5. Power
    actual_power = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Power level (kW) at which irradiation was performed"
    )

    # 6. Time In
    time_in = models.TimeField(
        help_text="Console time when irradiation began"
    )

    # 7. Time Out
    time_out = models.TimeField(
        help_text="Console time when irradiation ended"
    )

    # 8. Total Time
    TIME_UNIT_CHOICES = [
        ('min', 'minutes'),
        ('hr', 'hours'),
        ('sec', 'seconds'),
    ]
    total_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Total irradiation time"
    )
    total_time_unit = models.CharField(
        max_length=10,
        choices=TIME_UNIT_CHOICES,
        default='min',
        help_text="Unit for total time"
    )

    # 9. Dose Rate @ 1 foot
    measured_dose_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="1 foot dose rate (mrem/hr) from sample at initial handling"
    )

    # 10. Decay Time
    decay_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Approximate decay time between end of irradiation and dose rate measurement"
    )
    decay_time_unit = models.CharField(
        max_length=10,
        choices=TIME_UNIT_CHOICES,
        default='min',
        help_text="Unit for decay time"
    )

    # 11. Initials
    operator_initials = models.CharField(
        max_length=10,
        help_text="Console operator or experimenter initials"
    )

    # Additional tracking fields
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this irradiation"
    )

    class Meta:
        ordering = ['-irradiation_date', '-time_in']
        verbose_name = 'Sample Irradiation Log'
        verbose_name_plural = 'Sample Irradiation Logs'

    def __str__(self):
        sample_display = self.sample.sample_id if self.sample else self.sample_id_text
        return f"{sample_display} - {self.irradiation_date} ({self.irf.irf_number})"

    def get_sample_id(self):
        """Get the sample ID, preferring linked Sample over text field"""
        return self.sample.sample_id if self.sample else self.sample_id_text

    def fluence(self):
        """
        Calculate total fluence (kW-hrs)
        Fluence = Power × Time
        Converts time to hours based on unit
        """
        power_kw = float(self.actual_power)
        time = float(self.total_time)

        # Convert time to hours based on unit
        if self.total_time_unit == 'hr':
            time_hours = time
        elif self.total_time_unit == 'min':
            time_hours = time / 60.0
        elif self.total_time_unit == 'sec':
            time_hours = time / 3600.0
        else:
            # Default to minutes if unknown
            time_hours = time / 60.0

        return power_kw * time_hours

    def within_limits(self):
        """Check if irradiation is within IRF limits"""
        within_power = self.actual_power <= self.irf.max_power
        within_time = self.total_time <= self.irf.max_time
        return within_power and within_time


# ========================================
# ACTIVATION ANALYSIS MODELS
# ========================================

class FluxConfiguration(models.Model):
    """
    Stores neutron flux values for each irradiation location at reference power
    Used for activation analysis calculations
    """

    location = models.CharField(
        max_length=50,
        choices=LOCATION_CHOICES,
        unique=True,
        help_text="Irradiation location"
    )

    # Reference power for flux measurements
    reference_power = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=200.0,
        help_text="Reference power in kW (default: 200 kW)"
    )

    # Thermal neutron flux (E < 0.5 eV)
    thermal_flux = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Thermal neutron flux at reference power (n/cm²/s)"
    )

    # Fast neutron flux (E > 0.1 MeV)
    fast_flux = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Fast neutron flux at reference power (n/cm²/s)"
    )

    # Optional: intermediate flux for multi-group calculations
    intermediate_flux = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Intermediate neutron flux (0.5 eV < E < 0.1 MeV) at reference power (n/cm²/s)"
    )

    # Cadmium ratio (for thermal/epithermal characterization)
    cadmium_ratio = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cadmium ratio for this location (optional)"
    )

    notes = models.TextField(
        blank=True,
        help_text="Additional notes about flux measurements"
    )

    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['location']
        verbose_name = 'Flux Configuration'
        verbose_name_plural = 'Flux Configurations'

    def __str__(self):
        return f"{self.get_location_display()} - φ_th={self.thermal_flux:.2e} n/cm²/s"

    def get_scaled_fluxes(self, power_kw):
        """
        Get flux values scaled to a different power level
        Assumes linear scaling with power

        Args:
            power_kw: Power in kW

        Returns:
            dict with thermal_flux, fast_flux, intermediate_flux
        """
        scale_factor = float(power_kw) / float(self.reference_power)

        return {
            'thermal_flux': float(self.thermal_flux) * scale_factor,
            'fast_flux': float(self.fast_flux) * scale_factor,
            'intermediate_flux': float(self.intermediate_flux) * scale_factor if self.intermediate_flux else 0.0,
            'scale_factor': scale_factor
        }


class SampleComposition(models.Model):
    """
    Stores elemental composition of a sample
    Multiple elements can compose a single sample
    """

    COMPOSITION_TYPE_CHOICES = [
        ('wt', 'Weight Percent (wt%)'),
        ('at', 'Atomic Percent (at%)'),
    ]

    sample = models.ForeignKey(
        Sample,
        on_delete=models.CASCADE,
        related_name='composition_elements',
        help_text="Sample this composition belongs to"
    )

    element = models.CharField(
        max_length=3,
        help_text="Element symbol (e.g., Au, Al, Cu)"
    )

    # Natural isotopic abundance or specific isotope
    isotope = models.CharField(
        max_length=10,
        blank=True,
        help_text="Specific isotope (e.g., Au-197) or blank for natural abundance"
    )

    # Composition fraction
    fraction = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage of this element in the sample"
    )

    composition_type = models.CharField(
        max_length=2,
        choices=COMPOSITION_TYPE_CHOICES,
        default='wt',
        help_text="Type of composition (weight % or atomic %)"
    )

    order = models.IntegerField(
        default=0,
        help_text="Display order"
    )

    class Meta:
        ordering = ['sample', 'order']
        verbose_name = 'Sample Composition'
        verbose_name_plural = 'Sample Compositions'
        unique_together = ['sample', 'element', 'isotope']

    def __str__(self):
        isotope_str = f"-{self.isotope}" if self.isotope else ""
        return f"{self.element}{isotope_str}: {self.fraction}% ({self.composition_type})"


class ActivationResult(models.Model):
    """
    Caches calculated activation analysis results for samples
    Stores isotopic inventory after all irradiations
    """

    sample = models.ForeignKey(
        Sample,
        on_delete=models.CASCADE,
        related_name='activation_results',
        help_text="Sample these results belong to"
    )

    # Hash of irradiation history to detect changes
    irradiation_hash = models.CharField(
        max_length=64,
        help_text="SHA256 hash of irradiation log IDs and parameters"
    )

    # Calculation timestamp
    calculated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this calculation was performed"
    )

    # Reference time for activities (usually time of last irradiation end)
    reference_time = models.DateTimeField(
        help_text="Reference time for reported activities"
    )

    # Total activity
    total_activity_bq = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        help_text="Total activity in Becquerels at reference time"
    )

    # Dose rate estimate (using 6CE rule or detailed calculation)
    estimated_dose_rate_1ft = models.FloatField(
        null=True,
        blank=True,
        help_text="Estimated dose rate at 1 foot (mrem/hr)"
    )

    # JSON field to store complete isotopic inventory
    # Format: {isotope: {activity_bq, atoms, mass_g, contribution_to_dose}}
    isotopic_inventory = models.JSONField(
        help_text="Complete isotopic inventory as JSON"
    )

    # Calculation parameters
    calculation_method = models.CharField(
        max_length=50,
        default='multi-group',
        help_text="Method used (one-group, multi-group, etc.)"
    )

    number_of_isotopes = models.IntegerField(
        help_text="Number of isotopes in inventory"
    )

    # Success flag
    calculation_successful = models.BooleanField(
        default=True,
        help_text="Whether calculation completed successfully"
    )

    error_message = models.TextField(
        blank=True,
        help_text="Error message if calculation failed"
    )

    notes = models.TextField(
        blank=True,
        help_text="Calculation notes and assumptions"
    )

    class Meta:
        ordering = ['-calculated_at']
        verbose_name = 'Activation Result'
        verbose_name_plural = 'Activation Results'
        # Keep only most recent result per sample
        unique_together = ['sample', 'irradiation_hash']

    def __str__(self):
        return f"{self.sample.sample_id} - {self.calculated_at.strftime('%Y-%m-%d %H:%M')} ({self.number_of_isotopes} isotopes)"


class ActivationTimeline(models.Model):
    """
    Stores activation timeline - intermediate states after each irradiation/decay step
    Enables visualization of activity evolution over time
    """

    activation_result = models.ForeignKey(
        ActivationResult,
        on_delete=models.CASCADE,
        related_name='timeline_entries',
        help_text="Parent activation result this timeline belongs to"
    )

    # Step identification
    step_number = models.IntegerField(
        help_text="Sequential step number (0=initial, 1=after first irr, etc.)"
    )

    STEP_TYPE_CHOICES = [
        ('initial', 'Initial State'),
        ('irradiation', 'After Irradiation'),
        ('decay', 'After Decay Period'),
        ('current', 'Current Date'),
    ]

    step_type = models.CharField(
        max_length=20,
        choices=STEP_TYPE_CHOICES,
        help_text="Type of timeline step"
    )

    # Timestamp for this step
    step_datetime = models.DateTimeField(
        help_text="Date/time of this step in the timeline"
    )

    # Description
    description = models.CharField(
        max_length=200,
        help_text="Human-readable description of this step"
    )

    # Inventory at this step
    inventory = models.JSONField(
        help_text="Isotopic inventory (atoms) at this step: {isotope: n_atoms}"
    )

    # Activities at this step
    total_activity_bq = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        help_text="Total activity at this step (Bq)"
    )

    # Dominant isotopes (for quick reference)
    dominant_isotopes = models.JSONField(
        null=True,
        blank=True,
        help_text="Top isotopes by activity: {isotope: activity_bq}"
    )

    # Dose rate at this step
    estimated_dose_rate_1ft = models.FloatField(
        null=True,
        blank=True,
        help_text="Estimated dose rate at 1 foot (mrem/hr)"
    )

    # Optional: link to specific irradiation log if this step is after an irradiation
    irradiation_log = models.ForeignKey(
        'SampleIrradiationLog',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timeline_entries',
        help_text="Irradiation log if this step follows an irradiation"
    )

    # Time deltas for decay periods
    decay_time_seconds = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Decay time in seconds (for decay steps)"
    )

    class Meta:
        ordering = ['activation_result', 'step_number']
        verbose_name = 'Activation Timeline Entry'
        verbose_name_plural = 'Activation Timeline Entries'
        unique_together = ['activation_result', 'step_number']

    def __str__(self):
        return f"{self.activation_result.sample.sample_id} - Step {self.step_number}: {self.description}"

    def get_activity_mci(self):
        """Get total activity in mCi"""
        return float(self.total_activity_bq) / 3.7e10 * 1000

    def get_activity_ci(self):
        """Get total activity in Ci"""
        return float(self.total_activity_bq) / 3.7e10

    def get_decay_time_display(self):
        """Format decay time for display"""
        if not self.decay_time_seconds:
            return None

        seconds = self.decay_time_seconds
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60

        if days > 0:
            return f"{days} days, {hours} hours"
        elif hours > 0:
            return f"{hours} hours, {minutes} minutes"
        else:
            return f"{minutes} minutes"

    def get_dominant_isotopes(self, min_fraction=0.01):
        """
        Get isotopes contributing more than min_fraction to total activity

        Args:
            min_fraction: Minimum fraction of total activity (default 1%)

        Returns:
            List of isotopes sorted by activity
        """
        inventory = self.isotopic_inventory
        total_activity = float(self.total_activity_bq)

        dominant = []
        for isotope, data in inventory.items():
            activity = data.get('activity_bq', 0)
            fraction = activity / total_activity if total_activity > 0 else 0

            if fraction >= min_fraction:
                dominant.append({
                    'isotope': isotope,
                    'activity_bq': activity,
                    'activity_ci': activity / 3.7e10,
                    'fraction': fraction,
                    'half_life': data.get('half_life', 'unknown')
                })

        # Sort by activity descending
        dominant.sort(key=lambda x: x['activity_bq'], reverse=True)
        return dominant
