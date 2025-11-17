#!/usr/bin/env python
"""
Manual calculation of gold foil activation to verify the code
"""

import numpy as np
from pyne import nucname, data as pyne_data

# Constants
AVOGADRO = 6.022e23  # atoms/mol
LAMBDA_LN2 = 0.693147

# Parameters
gold_mass_g = 2.5
thermal_flux = 2.5e12  # n/cm²/s
irradiation_time_hr = 1.0
irradiation_time_s = irradiation_time_hr * 3600  # seconds
decay_time_days = 3.0
decay_time_s = decay_time_days * 86400  # seconds

print("="*80)
print("MANUAL GOLD FOIL ACTIVATION CALCULATION")
print("="*80)

print(f"\nParameters:")
print(f"  Gold mass: {gold_mass_g} g")
print(f"  Thermal flux: {thermal_flux:.2e} n/cm²/s")
print(f"  Irradiation time: {irradiation_time_hr} hr = {irradiation_time_s} s")
print(f"  Decay time: {decay_time_days} days = {decay_time_s} s")

# Step 1: Calculate number of Au-197 atoms
Au197_mass_number = 197  # g/mol
n_atoms_Au197 = (gold_mass_g * AVOGADRO) / Au197_mass_number
print(f"\nStep 1: Initial Au-197 atoms")
print(f"  N₀(Au-197) = ({gold_mass_g} g × {AVOGADRO:.3e}) / {Au197_mass_number}")
print(f"  N₀(Au-197) = {n_atoms_Au197:.3e} atoms")

# Step 2: Get cross-section for Au-197(n,γ)Au-198
# Use PyNE or fallback
try:
    from pyne.xs import data_source

    # Try to get thermal cross-section from PyNE
    isotope = 'Au-197'
    nuc_id = nucname.id(isotope)

    try:
        sds = data_source.SimpleDataSource()
        xs_data = sds.reaction(nuc_id, 'gamma')
        if xs_data and 'xs' in xs_data:
            xs_array = xs_data['xs']
            if len(xs_array) > 0:
                sigma_barns = xs_array[-1]  # Thermal cross-section
                print(f"\n✓ Got cross-section from PyNE SimpleDataSource")
    except:
        pass

    if 'sigma_barns' not in locals():
        # Fallback: use known value for Au-197
        sigma_barns = 98.65  # barns (well-known value)
        print(f"\n✓ Using literature value for Au-197 thermal capture cross-section")

except ImportError:
    sigma_barns = 98.65
    print(f"\n✓ Using literature value (PyNE not available)")

sigma_cm2 = sigma_barns * 1e-24  # Convert barns to cm²

print(f"\nStep 2: Neutron capture cross-section")
print(f"  σ(Au-197, n,γ) = {sigma_barns:.2f} barns = {sigma_cm2:.3e} cm²")

# Step 3: Get half-life of Au-198
try:
    Au198_nuc_id = nucname.id('Au-198')
    half_life_s = pyne_data.half_life(Au198_nuc_id)
    print(f"\n✓ Got half-life from PyNE")
except:
    half_life_s = 2.6955 * 86400  # 2.6955 days in seconds
    print(f"\n✓ Using literature value for Au-198 half-life")

half_life_days = half_life_s / 86400
lambda_decay = LAMBDA_LN2 / half_life_s

print(f"\nStep 3: Au-198 decay constant")
print(f"  t½(Au-198) = {half_life_days:.4f} days = {half_life_s:.2e} s")
print(f"  λ = ln(2) / t½ = {lambda_decay:.3e} s⁻¹")

# Step 4: Calculate production rate
R = sigma_cm2 * thermal_flux * n_atoms_Au197  # atoms/s
print(f"\nStep 4: Au-198 production rate during irradiation")
print(f"  R = σ × φ × N₀")
print(f"  R = {sigma_cm2:.3e} cm² × {thermal_flux:.3e} n/cm²/s × {n_atoms_Au197:.3e} atoms")
print(f"  R = {R:.3e} atoms/s")

# Step 5: Calculate Au-198 atoms at end of irradiation (saturation formula)
# N(t) = (R/λ) × [1 - exp(-λt)]
N_Au198_EOI = (R / lambda_decay) * (1 - np.exp(-lambda_decay * irradiation_time_s))
print(f"\nStep 5: Au-198 atoms at end of irradiation (EOI)")
print(f"  N(EOI) = (R/λ) × [1 - exp(-λt)]")
print(f"  N(EOI) = ({R:.3e} / {lambda_decay:.3e}) × [1 - exp(-{lambda_decay:.3e} × {irradiation_time_s})]")
print(f"  N(EOI) = {N_Au198_EOI:.3e} atoms")

# Step 6: Calculate activity at EOI
activity_EOI_Bq = lambda_decay * N_Au198_EOI
activity_EOI_Ci = activity_EOI_Bq / 3.7e10
activity_EOI_mCi = activity_EOI_Ci * 1000

print(f"\nStep 6: Activity at end of irradiation")
print(f"  A(EOI) = λ × N(EOI)")
print(f"  A(EOI) = {lambda_decay:.3e} × {N_Au198_EOI:.3e}")
print(f"  A(EOI) = {activity_EOI_Bq:.3e} Bq")
print(f"  A(EOI) = {activity_EOI_mCi:.3e} mCi")
print(f"  A(EOI) = {activity_EOI_Ci:.3e} Ci")

# Step 7: Decay to current time
N_Au198_current = N_Au198_EOI * np.exp(-lambda_decay * decay_time_s)
activity_current_Bq = lambda_decay * N_Au198_current
activity_current_Ci = activity_current_Bq / 3.7e10
activity_current_mCi = activity_current_Ci * 1000

print(f"\nStep 7: Activity after {decay_time_days} days of decay")
print(f"  A(t) = A(EOI) × exp(-λt)")
print(f"  A(t) = {activity_EOI_Bq:.3e} × exp(-{lambda_decay:.3e} × {decay_time_s})")
print(f"  A(t) = {activity_current_Bq:.3e} Bq")
print(f"  A(t) = {activity_current_mCi:.3e} mCi")
print(f"  A(t) = {activity_current_Ci:.3e} Ci")

# Step 8: Calculate dose rate using 6CE rule
# Get gamma energy
try:
    Au198_nuc_id = nucname.id('Au-198')
    intensities = pyne_data.gamma_photon_intensity(Au198_nuc_id)
    energies = pyne_data.gamma_energy(Au198_nuc_id)

    total_gamma_energy_kev = sum(energies[i][0] * intensities[i][0] / 100.0
                                 for i in range(len(energies)))
    gamma_energy_mev = total_gamma_energy_kev / 1000.0
    print(f"\n✓ Got gamma energy from PyNE")
except:
    gamma_energy_mev = 0.412  # MeV (approximate)
    print(f"\n✓ Using approximate gamma energy")

print(f"\nStep 8: Dose rate at 1 foot")
print(f"  E_γ(Au-198) = {gamma_energy_mev:.3f} MeV per decay")
print(f"  Using 6CE rule: Dose rate = 6 × C × E")

dose_rate_mrem_hr = 6.0 * activity_current_Ci * gamma_energy_mev

print(f"  Dose rate = 6 × {activity_current_Ci:.3e} Ci × {gamma_energy_mev:.3f} MeV")
print(f"  Dose rate = {dose_rate_mrem_hr:.2f} mrem/hr at 1 foot")

print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")
print(f"After {irradiation_time_hr} hr irradiation at {thermal_flux:.2e} n/cm²/s:")
print(f"  Activity at EOI:  {activity_EOI_mCi:.2f} mCi ({activity_EOI_Ci:.3e} Ci)")
print(f"After {decay_time_days} days decay:")
print(f"  Current activity: {activity_current_mCi:.2f} mCi ({activity_current_Ci:.3e} Ci)")
print(f"  Dose rate:        {dose_rate_mrem_hr:.2f} mrem/hr at 1 foot")
print(f"{'='*80}")

# Expected ranges for validation
print(f"\nVALIDATION:")
if activity_current_mCi > 1000:
    print(f"✓ Activity is in expected range (several hundred to thousands of mCi)")
elif activity_current_mCi > 100:
    print(f"✓ Activity is reasonable (hundreds of mCi)")
else:
    print(f"⚠️  Activity seems LOW (expected > 100 mCi for this scenario)")

if dose_rate_mrem_hr > 100:
    print(f"✓ Dose rate is in expected range (> 100 mrem/hr)")
elif dose_rate_mrem_hr > 10:
    print(f"⚠️  Dose rate is lower than expected (expected > 100 mrem/hr)")
else:
    print(f"⚠️  Dose rate is VERY LOW (expected > 100 mrem/hr)")
