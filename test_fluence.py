#!/usr/bin/env python3
"""
Test fluence calculation with different time units
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'irfdb.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from irradiation.models import SampleIrradiationLog, IrradiationRequestForm
from datetime import date, time

print("=" * 60)
print("FLUENCE CALCULATION TEST")
print("=" * 60)

# Get or create test IRF
irf, _ = IrradiationRequestForm.objects.get_or_create(
    irf_number='TEST-FLUENCE',
    defaults={
        'version_number': 1,
        'sample_description': 'Fluence test',
        'requester_name': 'Test',
        'status': 'draft',
        'max_power': Decimal('200.0'),
        'max_time': Decimal('24.0'),
        'max_time_unit': 'hr',
        'max_mass': Decimal('10.0'),
        'max_mass_unit': 'g',
        'expected_dose_rate': Decimal('100.0')
    }
)

print(f"\nUsing IRF: {irf.irf_number}")
print(f"Testing power: 200 kW")
print(f"\n{'Time':<15} {'Unit':<10} {'Fluence (kW-hrs)':<20} {'Expected':<20}")
print("-" * 60)

test_cases = [
    (4.0, 'hr', 800.0),      # 200 kW × 4 hrs = 800 kW-hrs
    (240.0, 'min', 800.0),   # 200 kW × 4 hrs (240 min) = 800 kW-hrs
    (14400.0, 'sec', 800.0), # 200 kW × 4 hrs (14400 sec) = 800 kW-hrs
    (1.0, 'hr', 200.0),      # 200 kW × 1 hr = 200 kW-hrs
    (30.0, 'min', 100.0),    # 200 kW × 0.5 hrs (30 min) = 100 kW-hrs
]

for test_time, unit, expected in test_cases:
    # Create test log
    log = SampleIrradiationLog(
        irf=irf,
        irradiation_date=date.today(),
        sample_id_text='TEST-SAMPLE',
        experimenter_name='Test User',
        actual_location='bare_rabbit',
        actual_power=Decimal('200.0'),
        time_in=time(10, 0),
        time_out=time(14, 0),
        total_time=Decimal(str(test_time)),
        total_time_unit=unit,
        measured_dose_rate=Decimal('100.0'),
        decay_time=Decimal('10.0'),
        decay_time_unit='min',
        operator_initials='TU'
    )

    # Calculate fluence
    calculated = log.fluence()

    # Check if correct
    status = "✓" if abs(calculated - expected) < 0.01 else "❌"

    print(f"{test_time:<15.1f} {unit:<10} {calculated:<20.2f} {expected:<20.2f} {status}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)

# Cleanup
irf.delete()
