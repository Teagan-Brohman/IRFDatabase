#!/usr/bin/env python
"""
Test script to verify dose rate calculation for gold foil activation

This script:
1. Creates a 2.5g gold foil sample
2. Sets up flux configuration for bare rabbit
3. Simulates irradiation at 200 kW for 1 hour
4. Calculates activation and dose rate
5. Checks if the dose rate is reasonable
"""

import os
import sys
import django
from datetime import datetime, date, time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'irfdb.settings')
django.setup()

from django.utils import timezone
from irradiation.models import Sample, SampleComposition, FluxConfiguration, SampleIrradiationLog, IrradiationRequestForm
from irradiation.activation import ActivationCalculator
from decimal import Decimal

def main():
    print("=" * 80)
    print("GOLD FOIL DOSE RATE TEST")
    print("=" * 80)

    # Clean up any existing test data
    Sample.objects.filter(sample_id='TEST-AU-FOIL').delete()
    FluxConfiguration.objects.filter(location='bare_rabbit').delete()
    IrradiationRequestForm.objects.filter(irf_number='TEST-001').delete()

    # 1. Create gold foil sample (2.5g)
    print("\n1. Creating 2.5g gold foil sample...")
    sample = Sample.objects.create(
        sample_id='TEST-AU-FOIL',
        name='Test Gold Foil',
        description='2.5g gold foil for dose rate testing',
        material_type='Au',
        physical_form='foil',
        mass=Decimal('2.5'),
        mass_unit='g'
    )

    # Add composition (100% natural gold = Au-197)
    SampleComposition.objects.create(
        sample=sample,
        element='Au',
        isotope='197',  # Au-197 (100% natural abundance)
        fraction=Decimal('100.0'),
        composition_type='wt'
    )
    print(f"   ✓ Created sample: {sample.sample_id} ({sample.mass} {sample.mass_unit})")

    # 2. Set up flux configuration for bare rabbit
    # Typical research reactor thermal flux: ~2.5e12 n/cm²/s at 200 kW
    # Fast flux is typically 10-20% of thermal
    print("\n2. Setting up flux configuration for bare rabbit...")
    flux_config = FluxConfiguration.objects.create(
        location='bare_rabbit',
        reference_power=Decimal('200.0'),
        thermal_flux=Decimal('2.5e12'),  # 2.5 × 10^12 n/cm²/s
        fast_flux=Decimal('5.0e11'),     # 5.0 × 10^11 n/cm²/s
        intermediate_flux=Decimal('1.0e12')  # 1.0 × 10^12 n/cm²/s
    )
    print(f"   ✓ Thermal flux: {flux_config.thermal_flux:.2e} n/cm²/s at {flux_config.reference_power} kW")
    print(f"   ✓ Fast flux: {flux_config.fast_flux:.2e} n/cm²/s")

    # 3. Create an IRF for this test
    print("\n3. Creating test IRF...")
    irf = IrradiationRequestForm.objects.create(
        irf_number='TEST-001',
        sample_description='Test gold foil',
        physical_form='foil',
        encapsulation='poly_vial',
        irradiation_location='bare_rabbit',
        max_power=Decimal('200.0'),
        max_power_unit='kw',
        max_time=Decimal('60.0'),
        max_time_unit='min',
        max_mass=Decimal('5.0'),
        max_mass_unit='g',
        expected_dose_rate=Decimal('1000.0'),
        dose_rate_basis='calculations',
        reactivity_worth=Decimal('0.01'),
        reactivity_basis='experience'
    )
    print(f"   ✓ Created IRF: {irf.irf_number}")

    # 4. Create irradiation log (200 kW for 1 hour)
    print("\n4. Creating irradiation log (200 kW for 1 hour)...")
    irr_log = SampleIrradiationLog.objects.create(
        irf=irf,
        sample=sample,
        irradiation_date=date.today(),
        sample_id_text='TEST-AU-FOIL',
        experimenter_name='Test User',
        actual_location='bare_rabbit',
        actual_power=Decimal('200.0'),  # 200 kW
        time_in=time(10, 0, 0),
        time_out=time(11, 0, 0),
        total_time=Decimal('60.0'),  # 60 minutes = 1 hour
        total_time_unit='min',
        measured_dose_rate=Decimal('0.0'),  # To be calculated
        decay_time=Decimal('0.0'),
        decay_time_unit='min',
        operator_initials='TEST'
    )
    print(f"   ✓ Created irradiation: {irr_log.actual_power} kW for {irr_log.total_time} {irr_log.total_time_unit}")

    # 5. Calculate activation
    print("\n5. Calculating activation and dose rate...")
    print("=" * 80)

    calculator = ActivationCalculator(use_multigroup=False)

    # Get irradiation logs and flux configs
    logs = sample.irradiation_logs.all().order_by('irradiation_date')
    flux_configs = {fc.location: fc for fc in FluxConfiguration.objects.all()}

    # Run calculation
    results = calculator.calculate_activation(
        sample=sample,
        irradiation_logs=logs,
        flux_configs=flux_configs,
        min_activity_fraction=0.001,
        use_cache=False
    )

    if not results.get('calculation_successful'):
        print(f"❌ Calculation failed: {results.get('error_message', 'Unknown error')}")
        return 1

    # Display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    total_activity_bq = results['total_activity_bq']
    total_activity_ci = total_activity_bq / 3.7e10
    total_activity_mci = total_activity_ci * 1000

    print(f"\nTotal Activity:")
    print(f"  {total_activity_bq:.2e} Bq")
    print(f"  {total_activity_ci:.2e} Ci")
    print(f"  {total_activity_mci:.2f} mCi")

    dose_rate = results.get('estimated_dose_rate_1ft', 0)
    print(f"\nEstimated Dose Rate at 1 foot:")
    print(f"  {dose_rate:.2f} mrem/hr")

    # Display isotopes
    print(f"\nDominant Isotopes:")
    isotopes = results.get('isotopes', {})
    sorted_isotopes = sorted(isotopes.items(), key=lambda x: x[1]['activity_bq'], reverse=True)

    for isotope, data in sorted_isotopes[:10]:
        activity_ci = data['activity_ci']
        activity_mci = activity_ci * 1000
        fraction = data['fraction']
        half_life = data.get('half_life_display', 'unknown')
        print(f"  {isotope:12s}: {activity_mci:8.2f} mCi ({fraction*100:5.1f}%)  t½={half_life}")

    # Calculate expected dose rate manually for comparison
    print("\n" + "=" * 80)
    print("MANUAL CALCULATION FOR VERIFICATION")
    print("=" * 80)

    # Gold foil activation calculation
    # Au-197 + n -> Au-198 (t½ = 2.7 days)
    # Cross section: σ = 98.65 barns
    # Flux: φ = 2.5e12 n/cm²/s (thermal)
    # Mass: 2.5 g
    # Time: 3600 seconds

    print("\nGold-197 activation:")
    print("  Natural abundance: 100%")
    print("  Cross section: 98.65 barns")
    print("  Product: Au-198 (t½ = 2.7 days)")

    # Calculate number of Au-197 atoms
    mass_g = 2.5
    atomic_mass = 197
    avogadro = 6.022e23
    n_atoms = (mass_g / atomic_mass) * avogadro
    print(f"\n  Number of Au-197 atoms: {n_atoms:.3e}")

    # Calculate activation
    sigma_barns = 98.65
    sigma_cm2 = sigma_barns * 1e-24
    flux = 2.5e12  # n/cm²/s
    time_s = 3600  # 1 hour
    half_life_s = 2.7 * 24 * 3600  # 2.7 days
    decay_const = 0.693 / half_life_s

    print(f"  Thermal flux: {flux:.2e} n/cm²/s")
    print(f"  Cross section: {sigma_cm2:.2e} cm²")
    print(f"  Irradiation time: {time_s} s")
    print(f"  Half-life: {half_life_s:.2e} s ({half_life_s/86400:.2f} days)")

    # Production with saturation
    production_rate = sigma_cm2 * flux * n_atoms
    saturation_factor = 1 - (2.71828 ** (-decay_const * time_s))
    n_au198 = (production_rate / decay_const) * saturation_factor

    print(f"\n  Production rate: {production_rate:.3e} atoms/s")
    print(f"  Saturation factor: {saturation_factor:.6f}")
    print(f"  Au-198 atoms produced: {n_au198:.3e}")

    # Activity immediately after irradiation
    activity_bq = decay_const * n_au198
    activity_ci = activity_bq / 3.7e10
    activity_mci = activity_ci * 1000

    print(f"\n  Activity (end of irradiation):")
    print(f"    {activity_bq:.2e} Bq")
    print(f"    {activity_ci:.2e} Ci")
    print(f"    {activity_mci:.2f} mCi")

    # Dose rate using 6 C E rule
    # Au-198 has two main gammas: 411.8 keV (95.5%) and 675.9 keV (1.1%)
    # Weighted average: ~420 keV = 0.42 MeV
    gamma_energy_mev = 0.412  # Primary gamma
    dose_rate_expected = 6.0 * activity_ci * gamma_energy_mev

    print(f"\n  Dose rate (6 C E rule):")
    print(f"    Gamma energy: {gamma_energy_mev} MeV")
    print(f"    Dose rate = 6 × {activity_ci:.2e} Ci × {gamma_energy_mev} MeV")
    print(f"    Expected: {dose_rate_expected:.2f} mrem/hr")

    # Compare with calculated value
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print(f"  Calculated dose rate: {dose_rate:.2f} mrem/hr")
    print(f"  Expected dose rate:   {dose_rate_expected:.2f} mrem/hr")

    ratio = dose_rate / dose_rate_expected if dose_rate_expected > 0 else 0
    print(f"  Ratio (calc/expected): {ratio:.2f}")

    if ratio < 0.1:
        print("\n  ❌ WARNING: Calculated dose rate is much lower than expected!")
        print("     This suggests there may be an issue with the dose rate calculation.")
    elif ratio > 10:
        print("\n  ❌ WARNING: Calculated dose rate is much higher than expected!")
        print("     This suggests there may be an issue with the dose rate calculation.")
    else:
        print("\n  ✓ Dose rate calculation appears reasonable (within order of magnitude)")

    print("\n" + "=" * 80)

    return 0

if __name__ == '__main__':
    sys.exit(main())
