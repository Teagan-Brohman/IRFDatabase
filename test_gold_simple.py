#!/usr/bin/env python
"""
Simplified test for gold foil activation - demonstrates the dose rate calculation bug
"""

import sys
sys.path.insert(0, '/home/teagan/IRFDatabase')

from pyne import nucname, data as pyne_data
import numpy as np

def test_gamma_energy_calculation():
    """Test the gamma energy calculation for Au-198"""

    print("="*80)
    print("AU-198 GAMMA ENERGY CALCULATION TEST")
    print("="*80)

    isotope = 'Au-198'
    nuc_id = nucname.id(isotope)

    # Get gamma data from PyNE
    intensities = pyne_data.gamma_photon_intensity(nuc_id)
    energies = pyne_data.gamma_energy(nuc_id)

    print(f"\nGamma emissions for {isotope}:")
    print(f"{'Energy (keV)':>15} {'Intensity (%)':>15} {'Contribution (keV/decay)':>25}")
    print("-"*60)

    total_intensity = 0
    total_energy_per_decay = 0

    for i in range(len(energies)):
        energy_kev = energies[i][0]
        intensity_pct = intensities[i][0]
        contribution = energy_kev * (intensity_pct / 100.0)  # keV per decay

        total_intensity += intensity_pct
        total_energy_per_decay += contribution

        print(f"{energy_kev:15.2f} {intensity_pct:15.4f} {contribution:25.2f}")

    print("-"*60)
    print(f"{'TOTAL':>15} {total_intensity:15.4f} {total_energy_per_decay:25.2f}")

    # Calculate weighted average (WRONG METHOD - what the code currently does)
    weighted_avg = sum(energies[i][0] * intensities[i][0] for i in range(len(energies))) / total_intensity

    print(f"\n{'='*80}")
    print("COMPARISON:")
    print(f"{'='*80}")
    print(f"WRONG (weighted average):   {weighted_avg:.3f} keV = {weighted_avg/1000:.3f} MeV")
    print(f"CORRECT (total energy):     {total_energy_per_decay:.3f} keV = {total_energy_per_decay/1000:.3f} MeV")
    print(f"Ratio (correct/wrong):      {total_energy_per_decay/weighted_avg:.2f}x")

    # Test dose rate calculation with 1 Ci source
    print(f"\n{'='*80}")
    print("DOSE RATE FOR 1 Ci Au-198 SOURCE:")
    print(f"{'='*80}")

    activity_ci = 1.0

    # Wrong calculation (current code)
    dose_wrong = 6.0 * activity_ci * (weighted_avg / 1000.0)
    print(f"WRONG:   {dose_wrong:.2f} mrem/hr  (using weighted avg)")

    # Correct calculation
    dose_correct = 6.0 * activity_ci * (total_energy_per_decay / 1000.0)
    print(f"CORRECT: {dose_correct:.2f} mrem/hr  (using total energy)")

    print(f"\nFor reference: 1 Ci of Au-198 should give ~{dose_correct:.0f} mrem/hr at 1 foot")
    print(f"The current code calculates only {dose_wrong:.0f} mrem/hr (factor of {dose_correct/dose_wrong:.1f}x too low)")

    return weighted_avg / 1000.0, total_energy_per_decay / 1000.0

if __name__ == '__main__':
    test_gamma_energy_calculation()
