#!/usr/bin/env python
"""
Test script for gold foil neutron activation and dose rate calculation

This script tests the activation of a 2.5g gold foil to verify dose rate calculations.
Expected: After high-flux irradiation, Au-198 should produce significant dose rates
(typically several hundred to thousands of mrem/hr, not just 3 mrem/hr).
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'irfdb.settings')
sys.path.insert(0, '/home/teagan/IRFDatabase')
django.setup()

from datetime import datetime, timedelta, time as dt_time
from django.utils import timezone
from irradiation.models import Sample, SampleComposition, FluxConfiguration, IrradiationRequestForm, SampleIrradiationLog
from irradiation.activation import ActivationCalculator
from decimal import Decimal

def main():
    print("="*80)
    print("GOLD FOIL ACTIVATION TEST")
    print("="*80)

    # Test parameters
    gold_mass_g = 2.5
    irradiation_power_kw = 200  # Full power
    irradiation_time_hr = 1.0   # 1 hour irradiation

    print(f"\nTest Parameters:")
    print(f"  Gold foil mass: {gold_mass_g} g")
    print(f"  Irradiation power: {irradiation_power_kw} kW")
    print(f"  Irradiation time: {irradiation_time_hr} hr")

    # Create or get flux configuration for "bare rabbit" location
    flux_config, created = FluxConfiguration.objects.get_or_create(
        location='bare rabbit',
        defaults={
            'thermal_flux': Decimal('2.5e12'),  # 2.5×10^12 n/cm²/s
            'fast_flux': Decimal('1.0e11'),     # 1.0×10^11 n/cm²/s
            'reference_power': Decimal('200.0'),
        }
    )
    if created:
        print(f"\n✓ Created flux configuration for '{flux_config.location}'")
    else:
        print(f"\n✓ Using existing flux configuration for '{flux_config.location}'")

    print(f"  Thermal flux: {flux_config.thermal_flux:.2e} n/cm²/s")
    print(f"  Fast flux: {flux_config.fast_flux:.2e} n/cm²/s")

    # Create sample (gold foil)
    sample, created = Sample.objects.get_or_create(
        sample_id='TEST-AU-FOIL',
        defaults={
            'material_type': 'Gold',
            'description': 'Test 2.5g gold foil for activation testing',
            'mass': Decimal(str(gold_mass_g)),
            'mass_unit': 'g',
        }
    )
    if created:
        print(f"\n✓ Created sample '{sample.sample_id}'")

        # Create composition (natural gold = 100% Au-197)
        SampleComposition.objects.create(
            sample=sample,
            element='Au',
            isotope='197',  # Au-197 (100% natural abundance)
            fraction=Decimal('100.0'),  # 100% gold
        )
        print(f"  Composition: 100% Au-197")
    else:
        print(f"\n✓ Using existing sample '{sample.sample_id}'")

    # Create IRF for the test
    irf, created = IrradiationRequestForm.objects.get_or_create(
        irf_number='TEST-001',
        defaults={
            'requester_name': 'Test User',
            'sample_description': 'Gold foil activation test',
            'physical_form': 'foil',
            'max_power': Decimal('200'),
            'max_time': Decimal('2'),
            'max_time_unit': 'hr',
            'max_mass': Decimal('10'),  # Required field
            'max_mass_unit': 'g',
            'status': 'approved',
        }
    )
    if created:
        print(f"\n✓ Created IRF '{irf.irf_number}'")
    else:
        print(f"\n✓ Using existing IRF '{irf.irf_number}'")

    # Create irradiation log
    irr_date = timezone.now().date() - timedelta(days=3)  # 3 days ago
    time_in = dt_time(10, 0)  # 10:00 AM
    time_out = dt_time(11, 0)  # 11:00 AM

    log, created = SampleIrradiationLog.objects.get_or_create(
        parent_irf=irf,
        irradiation_date=irr_date,
        time_in=time_in,
        defaults={
            'actual_location': 'bare rabbit',
            'actual_power': Decimal(str(irradiation_power_kw)),
            'total_time': Decimal(str(irradiation_time_hr)),
            'total_time_unit': 'hr',
            'time_out': time_out,
        }
    )
    if created:
        print(f"\n✓ Created irradiation log")
        print(f"  Date: {irr_date}")
        print(f"  Location: {log.actual_location}")
        print(f"  Power: {log.actual_power} kW")
        print(f"  Duration: {log.total_time} {log.total_time_unit}")
    else:
        print(f"\n✓ Using existing irradiation log")

    # Link sample to irradiation log
    if sample not in [log.sample for log in irf.irradiation_logs.all() if hasattr(log, 'sample')]:
        # Note: SampleIrradiationLog doesn't have a direct sample field in the model
        # It's linked through the IRF. For this test, we'll query directly.
        pass

    # Calculate activation
    print("\n" + "="*80)
    print("CALCULATING ACTIVATION...")
    print("="*80)

    calculator = ActivationCalculator(use_multigroup=False)

    # Get irradiation logs for this sample (in this test, we use the parent IRF's logs)
    irradiation_logs = SampleIrradiationLog.objects.filter(parent_irf=irf).order_by('irradiation_date', 'time_in')

    # Get flux configs
    flux_configs = {fc.location: fc for fc in FluxConfiguration.objects.all()}

    results = calculator.calculate_activation(
        sample=sample,
        irradiation_logs=irradiation_logs,
        flux_configs=flux_configs,
        min_activity_fraction=0.001,
        use_cache=False,
    )

    if results.get('calculation_successful'):
        print("\n✓ Calculation successful!")

        total_activity_bq = results.get('total_activity_bq', 0)
        total_activity_ci = total_activity_bq / 3.7e10
        total_activity_mci = total_activity_ci * 1000

        print(f"\nTotal Activity (at current date):")
        print(f"  {total_activity_bq:.3e} Bq")
        print(f"  {total_activity_mci:.3e} mCi")
        print(f"  {total_activity_ci:.3e} Ci")

        decay_days = results.get('decay_time_days', 0)
        print(f"\nDecay time from end of irradiation: {decay_days:.1f} days")

        dose_rate = results.get('estimated_dose_rate_1ft', 0)
        print(f"\n{'='*80}")
        print(f"DOSE RATE AT 1 FOOT: {dose_rate:.2f} mrem/hr")
        print(f"{'='*80}")

        # Check if dose rate is reasonable
        # For 2.5g gold after 1 hr at high flux, expect hundreds to thousands of mrem/hr
        if dose_rate < 10:
            print("\n⚠️  WARNING: Dose rate seems unreasonably LOW!")
            print("   Expected several hundred to thousand mrem/hr for this scenario.")
        elif dose_rate > 1e6:
            print("\n⚠️  WARNING: Dose rate seems unreasonably HIGH!")
        else:
            print("\n✓ Dose rate is in reasonable range")

        # Show dominant isotopes
        print(f"\nDominant Isotopes:")
        isotopes = results.get('isotopes', {})
        sorted_isotopes = sorted(isotopes.items(), key=lambda x: x[1]['activity_bq'], reverse=True)

        for isotope, data in sorted_isotopes[:5]:
            activity_ci = data['activity_ci']
            fraction = data.get('fraction', 0)
            half_life = data.get('half_life_display', 'unknown')
            print(f"  {isotope:12s}: {activity_ci:.3e} Ci ({fraction*100:5.2f}%), t½={half_life}")

        # Manual calculation for Au-198
        print(f"\n{'='*80}")
        print("MANUAL VERIFICATION FOR Au-198")
        print(f"{'='*80}")

        if 'Au-198' in isotopes:
            au198_data = isotopes['Au-198']
            au198_activity_ci = au198_data['activity_ci']

            # Get gamma energy from PyNE
            try:
                from pyne import nucname, data as pyne_data

                nuc_id = nucname.id('Au-198')

                # Get gamma data
                try:
                    intensities = pyne_data.gamma_photon_intensity(nuc_id)
                    energies = pyne_data.gamma_energy(nuc_id)

                    if intensities and energies:
                        print(f"\nAu-198 Gamma Emissions:")
                        total_gamma_energy_kev = 0
                        for i in range(len(energies)):
                            energy_kev = energies[i][0]
                            intensity_pct = intensities[i][0]
                            gamma_per_decay = intensity_pct / 100.0
                            contribution_kev = energy_kev * gamma_per_decay
                            total_gamma_energy_kev += contribution_kev
                            print(f"  {energy_kev:8.2f} keV × {intensity_pct:7.4f}% = {contribution_kev:8.2f} keV/decay")

                        total_gamma_energy_mev = total_gamma_energy_kev / 1000.0
                        print(f"\nTotal gamma energy per decay: {total_gamma_energy_mev:.3f} MeV")

                        # Calculate dose rate using 6CE rule
                        dose_rate_manual = 6.0 * au198_activity_ci * total_gamma_energy_mev
                        print(f"\nManual calculation (6CE rule):")
                        print(f"  Dose rate = 6 × {au198_activity_ci:.3e} Ci × {total_gamma_energy_mev:.3f} MeV")
                        print(f"  Dose rate = {dose_rate_manual:.2f} mrem/hr")

                        # Compare with code calculation
                        code_dose_rate = results.get('estimated_dose_rate_1ft', 0)
                        ratio = code_dose_rate / dose_rate_manual if dose_rate_manual > 0 else 0
                        print(f"\nComparison:")
                        print(f"  Code calculated: {code_dose_rate:.2f} mrem/hr")
                        print(f"  Manual calculated: {dose_rate_manual:.2f} mrem/hr")
                        print(f"  Ratio (code/manual): {ratio:.6f}")

                        if abs(ratio - 1.0) > 0.01:  # More than 1% difference
                            print(f"\n⚠️  MISMATCH DETECTED! Code is calculating {ratio:.2f}× the correct value")
                        else:
                            print(f"\n✓ Calculations match!")

                except Exception as e:
                    print(f"Could not get gamma data: {e}")

            except ImportError:
                print("PyNE not available for manual verification")
        else:
            print("Au-198 not found in results!")

    else:
        print("\n✗ Calculation failed!")
        error = results.get('error_message', 'Unknown error')
        print(f"  Error: {error}")

    print("\n" + "="*80)

if __name__ == '__main__':
    main()
