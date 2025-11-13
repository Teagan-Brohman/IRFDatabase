from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse


class IrradiationRequestForm(models.Model):
    """
    Main IRF model based on Missouri S&T SOP 702
    One IRF can have multiple sample irradiations
    """

    # IRF Identification
    irf_number = models.CharField(
        max_length=20,
        unique=True,
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
    LOCATION_CHOICES = [
        ('bare_rabbit', 'Bare Rabbit'),
        ('cad_rabbit', 'Cad Rabbit'),
        ('beam_port', 'Beam Port'),
        ('thermal_column', 'Thermal Column'),
        ('other', 'Other'),
    ]
    # Allow multiple locations (stored as comma-separated or use ManyToMany in future)
    irradiation_location = models.CharField(
        max_length=200,
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
        ordering = ['-irf_number']
        verbose_name = 'Irradiation Request Form'
        verbose_name_plural = 'Irradiation Request Forms'

    def __str__(self):
        return f"IRF {self.irf_number} - {self.sample_description[:50]}"

    def get_absolute_url(self):
        return reverse('irradiation:irf_detail', kwargs={'pk': self.pk})

    def is_approved(self):
        """Check if IRF has two approvals"""
        return bool(self.approver1_date and self.approver2_date)

    def total_irradiations(self):
        """Count total irradiations performed under this IRF"""
        return self.irradiation_logs.count()

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

    # 1. Date
    irradiation_date = models.DateField(
        help_text="Date of sample irradiation"
    )

    # 2. Sample ID
    sample_id = models.CharField(
        max_length=100,
        help_text="Sample identification number or name"
    )

    # 3. Experimenter's Name
    experimenter_name = models.CharField(
        max_length=200,
        help_text="Name of experimenter responsible for the sample"
    )

    # 4. Location
    actual_location = models.CharField(
        max_length=200,
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
    total_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Total irradiation time (minutes)"
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
        help_text="Approximate decay time (minutes) between end of irradiation and dose rate measurement"
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
        return f"{self.sample_id} - {self.irradiation_date} ({self.irf.irf_number})"

    def fluence(self):
        """Calculate total fluence (kW-hrs)"""
        return float(self.actual_power) * (float(self.total_time) / 60)

    def within_limits(self):
        """Check if irradiation is within IRF limits"""
        within_power = self.actual_power <= self.irf.max_power
        within_time = self.total_time <= self.irf.max_time
        return within_power and within_time
