#!/usr/bin/env python
"""
Create sample data for IRF Database demonstration
"""
import os
import sys
import django
from datetime import date, time

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'irfdb.settings')
django.setup()

from irradiation.models import IrradiationRequestForm, SampleIrradiationLog, Sample

# Clear existing sample data
print("Clearing existing sample data...")
SampleIrradiationLog.objects.all().delete()
Sample.objects.all().delete()
IrradiationRequestForm.objects.all().delete()

print("Creating sample IRFs and logs...")

# IRF 1: Gold Foil
irf1 = IrradiationRequestForm.objects.create(
    irf_number='24-001',
    sample_description='Gold foil samples for neutron activation analysis',
    physical_form='foil',
    encapsulation='poly_vial',
    irradiation_location='Bare Rabbit',
    max_power=200.00,
    max_time=60.00,
    max_mass=5.000,
    expected_dose_rate=500.00,
    dose_rate_basis='experience',
    dose_rate_reference_irf='23-045',
    reactivity_worth=0.030,
    reactivity_basis='default',
    requester_name='Dr. John Smith',
    requester_signature_date=date(2024, 1, 15),
    status='approved',
    reactivity_hazard='none',
    dose_rate_hazard='none',
    reactor_equipment_hazard='none',
    other_hazard='none',
    approver1_role='sro',
    approver1_name='Jane Doe',
    approver1_date=date(2024, 1, 16),
    approver2_role='manager',
    approver2_name='Robert Johnson',
    approver2_date=date(2024, 1, 16),
)
print(f"Created IRF {irf1.irf_number}")

# Create samples for IRF 1
sample1 = Sample.objects.create(
    sample_id='AU-001',
    name='Gold foil sample 1',
    material_type='Gold',
    physical_form='foil',
    mass=2.5,
    mass_unit='g',
)

sample2 = Sample.objects.create(
    sample_id='AU-002',
    name='Gold foil sample 2',
    material_type='Gold',
    physical_form='foil',
    mass=2.5,
    mass_unit='g',
)

# Add sample logs for IRF 1
log1 = SampleIrradiationLog.objects.create(
    irf=irf1,
    sample=sample1,
    irradiation_date=date(2024, 2, 1),
    experimenter_name='Dr. John Smith',
    actual_location='Bare Rabbit',
    actual_power=200.00,
    time_in=time(10, 0),
    time_out=time(11, 0),
    total_time=60.00,
    measured_dose_rate=485.00,
    decay_time=5.00,
    operator_initials='JD',
)
print(f"  - Created log: {sample1.sample_id}")

log2 = SampleIrradiationLog.objects.create(
    irf=irf1,
    sample=sample2,
    irradiation_date=date(2024, 2, 8),
    experimenter_name='Dr. John Smith',
    actual_location='Bare Rabbit',
    actual_power=200.00,
    time_in=time(14, 30),
    time_out=time(15, 30),
    total_time=60.00,
    measured_dose_rate=492.00,
    decay_time=5.00,
    operator_initials='JD',
)
print(f"  - Created log: {sample2.sample_id}")

# IRF 2: Soil Samples
irf2 = IrradiationRequestForm.objects.create(
    irf_number='24-002',
    sample_description='Soil samples for environmental analysis',
    physical_form='powder',
    encapsulation='poly_vial',
    irradiation_location='Cad Rabbit',
    max_power=150.00,
    max_time=120.00,
    max_mass=10.000,
    expected_dose_rate=100.00,
    dose_rate_basis='calculations',
    dose_rate_calculation_notes='Calculated using DR=6CE rule with expected activity',
    reactivity_worth=0.045,
    reactivity_basis='default',
    requester_name='Dr. Sarah Williams',
    requester_signature_date=date(2024, 3, 1),
    status='approved',
    reactivity_hazard='none',
    dose_rate_hazard='none',
    reactor_equipment_hazard='none',
    other_hazard='none',
    approver1_role='sro',
    approver1_name='Jane Doe',
    approver1_date=date(2024, 3, 2),
    approver2_role='health_physicist',
    approver2_name='Michael Chen',
    approver2_date=date(2024, 3, 2),
)
print(f"Created IRF {irf2.irf_number}")

# Create sample for IRF 2
sample3 = Sample.objects.create(
    sample_id='SOIL-A1',
    name='Soil sample A1',
    material_type='Soil',
    physical_form='powder',
    mass=8.0,
    mass_unit='g',
)

# Add sample log for IRF 2
log3 = SampleIrradiationLog.objects.create(
    irf=irf2,
    sample=sample3,
    irradiation_date=date(2024, 3, 15),
    experimenter_name='Dr. Sarah Williams',
    actual_location='Cad Rabbit',
    actual_power=150.00,
    time_in=time(9, 0),
    time_out=time(11, 0),
    total_time=120.00,
    measured_dose_rate=95.00,
    decay_time=10.00,
    operator_initials='MC',
)
print(f"  - Created log: {sample3.sample_id}")

# IRF 3: Medical Isotope Production
irf3 = IrradiationRequestForm.objects.create(
    irf_number='24-003',
    sample_description='Molybdenum targets for medical isotope production',
    physical_form='solid',
    physical_form_other='Pressed pellet',
    encapsulation='other',
    encapsulation_other='Aluminum capsule',
    irradiation_location='Beam Port',
    max_power=250.00,
    max_time=180.00,
    max_mass=15.000,
    expected_dose_rate=1500.00,
    dose_rate_basis='experience',
    dose_rate_reference_irf='23-089',
    reactivity_worth=0.080,
    reactivity_basis='experience',
    reactivity_reference_irf='23-089',
    requester_name='Dr. Emily Thompson',
    requester_signature_date=date(2024, 4, 10),
    request_comments='High priority medical isotope production for local hospital',
    status='approved',
    reactivity_hazard='none',
    dose_rate_hazard='other',
    dose_rate_hazard_notes='High dose rate expected. Special handling procedures required.',
    reactor_equipment_hazard='none',
    other_hazard='none',
    additional_restrictions='Use remote handling tools. Store in lead pig immediately after removal.',
    approver1_role='director',
    approver1_name='Dr. William Bonzer',
    approver1_date=date(2024, 4, 11),
    approver2_role='health_physicist',
    approver2_name='Michael Chen',
    approver2_date=date(2024, 4, 11),
)
print(f"Created IRF {irf3.irf_number}")

# Create sample for IRF 3
sample4 = Sample.objects.create(
    sample_id='MO-99-001',
    name='Molybdenum-99 target 1',
    material_type='Molybdenum',
    physical_form='pellet',
    mass=12.0,
    mass_unit='g',
)

log4 = SampleIrradiationLog.objects.create(
    irf=irf3,
    sample=sample4,
    irradiation_date=date(2024, 4, 20),
    experimenter_name='Dr. Emily Thompson',
    actual_location='Beam Port 1',
    actual_power=250.00,
    time_in=time(8, 0),
    time_out=time(11, 0),
    total_time=180.00,
    measured_dose_rate=1485.00,
    decay_time=15.00,
    operator_initials='WB',
    notes='Sample handled with remote tools. Stored in lead pig as per restrictions.',
)
print(f"  - Created log: {sample4.sample_id}")

# IRF 4: Pending approval
irf4 = IrradiationRequestForm.objects.create(
    irf_number='24-004',
    sample_description='Silicon wafers for semiconductor research',
    physical_form='solid',
    encapsulation='poly_vial',
    irradiation_location='Thermal Column',
    max_power=100.00,
    max_time=300.00,
    max_mass=20.000,
    expected_dose_rate=50.00,
    dose_rate_basis='unknown',
    reactivity_worth=0.000,
    reactivity_basis='default',
    requester_name='Dr. Alex Martinez',
    requester_signature_date=date(2024, 5, 1),
    status='pending_review',
    reactivity_hazard='none',
    dose_rate_hazard='none',
    reactor_equipment_hazard='none',
    other_hazard='none',
)
print(f"Created IRF {irf4.irf_number}")

# IRF 5: Draft
irf5 = IrradiationRequestForm.objects.create(
    irf_number='24-005',
    sample_description='Biological samples for radiation effects study',
    physical_form='liquid',
    encapsulation='poly_vial',
    irradiation_location='Bare Rabbit',
    max_power=50.00,
    max_time=30.00,
    max_mass=3.000,
    expected_dose_rate=25.00,
    dose_rate_basis='calculations',
    reactivity_worth=0.020,
    reactivity_basis='default',
    requester_name='Dr. Lisa Anderson',
    status='draft',
)
print(f"Created IRF {irf5.irf_number}")

print("\n✓ Sample data creation complete!")
print(f"Created {IrradiationRequestForm.objects.count()} IRFs")
print(f"Created {Sample.objects.count()} samples")
print(f"Created {SampleIrradiationLog.objects.count()} sample logs")
print("\nLogin credentials:")
print("  Username: admin")
print("  Password: admin123")
