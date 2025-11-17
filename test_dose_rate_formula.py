#!/usr/bin/env python
"""
Test to determine the correct dose rate formula
"""

# Known reference data
print("="*80)
print("DOSE RATE FORMULA INVESTIGATION")
print("="*80)

# Known fact: 1 Ci of Co-60 gives ~1400 mrem/hr at 1 foot
activity_ci = 1.0
gamma_energy_mev_co60 = 2.5  # Total energy per decay
distance_ft = 1.0
dose_rate_co60_ref = 1400  # mrem/hr

print(f"\nReference data for Co-60:")
print(f"  Activity: {activity_ci} Ci")
print(f"  Gamma energy: {gamma_energy_mev_co60} MeV per decay")
print(f"  Distance: {distance_ft} foot")
print(f"  Measured dose rate: {dose_rate_co60_ref} mrem/hr")

# If dose_rate = K × C × E
K_co60 = dose_rate_co60_ref / (activity_ci * gamma_energy_mev_co60)
print(f"\nIf dose_rate = K × C × E:")
print(f"  K = dose_rate / (C × E)")
print(f"  K = {dose_rate_co60_ref} / ({activity_ci} × {gamma_energy_mev_co60})")
print(f"  K = {K_co60:.0f}")

print(f"\nThe code currently uses K = 6 (the '6CE rule')")
print(f"  Ratio: {K_co60} / 6 = {K_co60/6:.0f}x")
print(f"  This means the code underpredicts by ~{K_co60/6:.0f}x")

# Check with Cs-137
print(f"\n" + "="*80)
print("Verification with Cs-137:")
print("="*80)

gamma_energy_mev_cs137 = 0.662  # MeV
dose_rate_cs137_ref = 330  # mrem/hr for 1 Ci at 1 foot (approximate)

K_cs137 = dose_rate_cs137_ref / (activity_ci * gamma_energy_mev_cs137)
print(f"  Cs-137: 1 Ci at 1 foot gives ~{dose_rate_cs137_ref} mrem/hr")
print(f"  Gamma energy: {gamma_energy_mev_cs137} MeV")
print(f"  K = {K_cs137:.0f}")

# Average K
K_avg = (K_co60 + K_cs137) / 2
print(f"\nAverage K from Co-60 and Cs-137: {K_avg:.0f}")

print(f"\n" + "="*80)
print("CONCLUSION:")
print("="*80)
print(f"The correct formula should be:")
print(f"  dose_rate (mrem/hr) = {K_avg:.0f} × C (Ci) × E (MeV)")
print(f"  NOT: dose_rate = 6 × C × E")
print(f"\nThe '6CE rule' is likely:")
print(f"  1. For a different distance (not 1 foot)")
print(f"  2. For different units (maybe R/hr, not mrem/hr)")
print(f"  3. An approximation with limited validity")
print(f"\nSuggested fix: Use K ≈ {K_avg:.0f} instead of 6")
