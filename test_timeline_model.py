#!/usr/bin/env python
"""
Test the ActivationTimeline model and verify it works correctly
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'irfdb.settings')
django.setup()

from datetime import datetime, timedelta, time
from decimal import Decimal
from irradiation.models import (
    Sample, SampleComposition, SampleIrradiationLog,
    FluxConfiguration, ActivationResult, ActivationTimeline,
    IrradiationRequestForm
)


def test_activation_timeline_model():
    """Test that ActivationTimeline model works correctly"""

    print("\n" + "="*80)
    print("Testing ActivationTimeline Model")
    print("="*80)

    # Cleanup any previous test data first
    print("\n0. Cleanup any previous test data...")
    Sample.objects.filter(sample_id__startswith='TEST-').delete()
    IrradiationRequestForm.objects.filter(irf_number__startswith='24-TEST').delete()
    print("   ✓ Cleanup complete")

    # Create a test sample
    print("\n1. Creating test sample...")
    sample = Sample.objects.create(
        sample_id="TEST-AU-001",
        material_type="Gold",
        mass=Decimal("1.0"),
        mass_unit="g",
        description="Test gold foil for timeline"
    )
    print(f"   ✓ Created sample: {sample.sample_id}")

    # Add composition
    SampleComposition.objects.create(
        sample=sample,
        element="Au",
        isotope=197,
        fraction=Decimal("100.0")
    )
    print(f"   ✓ Added Au-197 composition")

    # Get or create flux configuration
    print("\n2. Getting/creating flux configuration...")
    flux_config, created = FluxConfiguration.objects.get_or_create(
        location="bare_rabbit",
        defaults={
            'thermal_flux': Decimal("2.5e12"),
            'fast_flux': Decimal("1.0e11"),
            'intermediate_flux': Decimal("5.0e10"),
            'reference_power': Decimal("200.0")
        }
    )
    if created:
        print(f"   ✓ Created flux config for {flux_config.location}")
    else:
        print(f"   ✓ Using existing flux config for {flux_config.location}")

    # Create activation result (simulating completed calculation)
    print("\n3. Creating activation result...")
    activation_result = ActivationResult.objects.create(
        sample=sample,
        irradiation_hash="test_hash_12345",
        reference_time=datetime(2024, 3, 1, 11, 0),
        total_activity_bq=Decimal("1.0e10"),
        estimated_dose_rate_1ft=Decimal("100.0"),
        isotopic_inventory={"Au-198": {"activity_bq": 1.0e10}},
        calculation_method="multi-group",
        number_of_isotopes=1,
        calculation_successful=True
    )
    print(f"   ✓ Created activation result")

    # Create timeline entries
    print("\n4. Creating timeline entries...")

    # Initial state
    entry0 = ActivationTimeline.objects.create(
        activation_result=activation_result,
        step_number=0,
        step_type='initial',
        step_datetime=datetime(2024, 1, 14, 0, 0),
        description='Initial state (before irradiation)',
        inventory={"Au-197": 3.06e21},
        total_activity_bq=Decimal("0"),
        dominant_isotopes={}
    )
    print(f"   ✓ Created step 0: {entry0.description}")

    # After first irradiation
    entry1 = ActivationTimeline.objects.create(
        activation_result=activation_result,
        step_number=1,
        step_type='irradiation',
        step_datetime=datetime(2024, 1, 15, 14, 0),
        description='After 4-hour irradiation at bare_rabbit',
        inventory={"Au-197": 3.06e21, "Au-198": 1.06e16},
        total_activity_bq=Decimal("8.548e11"),  # 854.8 mCi
        dominant_isotopes={"Au-198": 8.548e11},
        estimated_dose_rate_1ft=Decimal("85.48"),
        
    )
    print(f"   ✓ Created step 1: {entry1.description}")

    # After decay period
    entry2 = ActivationTimeline.objects.create(
        activation_result=activation_result,
        step_number=2,
        step_type='decay',
        step_datetime=datetime(2024, 3, 1, 8, 59, 59),
        description='After 46-day decay period',
        inventory={"Au-197": 3.06e21, "Au-198": 7.75e10},
        total_activity_bq=Decimal("6.23e7"),  # 0.006 mCi
        dominant_isotopes={"Au-198": 6.23e7},
        estimated_dose_rate_1ft=Decimal("0.006"),
        decay_time_seconds=46 * 24 * 3600
    )
    print(f"   ✓ Created step 2: {entry2.description}")

    # After second irradiation
    entry3 = ActivationTimeline.objects.create(
        activation_result=activation_result,
        step_number=3,
        step_type='irradiation',
        step_datetime=datetime(2024, 3, 1, 11, 0),
        description='After 2-hour irradiation at bare_rabbit',
        inventory={"Au-197": 3.06e21, "Au-198": 5.37e15},
        total_activity_bq=Decimal("4.32e11"),  # 432 mCi
        dominant_isotopes={"Au-198": 4.32e11},
        estimated_dose_rate_1ft=Decimal("43.2"),
        
    )
    print(f"   ✓ Created step 3: {entry3.description}")

    # Current date
    entry4 = ActivationTimeline.objects.create(
        activation_result=activation_result,
        step_number=4,
        step_type='current',
        step_datetime=datetime.now(),
        description=f'Current date',
        inventory={"Au-197": 3.06e21, "Au-198": 1.30e-46},  # Completely decayed
        total_activity_bq=Decimal("0.0"),
        dominant_isotopes={},
        estimated_dose_rate_1ft=Decimal("0.0"),
        decay_time_seconds=(datetime.now() - datetime(2024, 3, 1, 11, 0)).total_seconds()
    )
    print(f"   ✓ Created step 4: {entry4.description}")

    # Test retrieval
    print("\n6. Testing timeline retrieval...")
    timeline = activation_result.timeline_entries.all().order_by('step_number')
    print(f"   ✓ Retrieved {timeline.count()} timeline entries")

    # Test helper methods
    print("\n7. Testing helper methods...")
    print(f"   Step 1 activity: {entry1.get_activity_mci():.2f} mCi")
    print(f"   Step 1 activity: {entry1.get_activity_ci():.2e} Ci")
    print(f"   Step 2 decay time: {entry2.get_decay_time_display()}")
    print(f"   Step 4 decay time: {entry4.get_decay_time_display()}")

    # Display timeline table
    print("\n8. Timeline Table:")
    print("-" * 100)
    print(f"{'Step':<6} {'Type':<12} {'DateTime':<20} {'Activity (mCi)':<15} {'Dose (mrem/hr)':<15} {'Description'}")
    print("-" * 100)

    for entry in timeline:
        activity_mci = entry.get_activity_mci()
        dose = float(entry.estimated_dose_rate_1ft) if entry.estimated_dose_rate_1ft else 0.0
        dt_str = entry.step_datetime.strftime('%Y-%m-%d %H:%M')

        print(f"{entry.step_number:<6} {entry.step_type:<12} {dt_str:<20} "
              f"{activity_mci:<15.3f} {dose:<15.2f} {entry.description[:50]}")

    print("-" * 100)

    # Test cleanup
    print("\n8. Cleanup test data...")
    sample.delete()  # Cascade deletes everything
    # Don't delete flux_config - it may be used by other tests
    print("   ✓ Test data cleaned up")

    print("\n" + "="*80)
    print("✓ ALL TESTS PASSED!")
    print("="*80)

    return True


if __name__ == '__main__':
    try:
        test_activation_timeline_model()
        print("\n✓ ActivationTimeline model is working correctly!\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
