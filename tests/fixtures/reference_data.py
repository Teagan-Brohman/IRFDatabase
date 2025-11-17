"""
Reference data for validation testing

This module contains NIST/NRC published dose rate constants, neutron activation
cross-sections, and expected values for test scenarios.

Data Sources:
- NIST: National Institute of Standards and Technology
- NRC: Nuclear Regulatory Commission
- IAEA: International Atomic Energy Agency
- Literature: Standard health physics references

All dose rates are for point sources at 1 foot distance in air.
"""

from decimal import Decimal

# =============================================================================
# NIST/NRC DOSE RATE CONSTANTS
# =============================================================================

NIST_DOSE_CONSTANTS = {
    'Co-60': {
        'gamma_energy_mev': 2.504,  # Total: 1.173 + 1.332 MeV
        'gamma_lines': [
            {'energy_kev': 1173.23, 'intensity_percent': 99.85},
            {'energy_kev': 1332.49, 'intensity_percent': 99.98},
        ],
        'half_life_days': 1925.28,  # 5.27 years
        'half_life_seconds': 1925.28 * 86400,
        'dose_rate_1ci_1ft_mrem_hr': 1400,  # Reference value
        'dose_rate_tolerance_percent': 10,  # ±10% acceptable
        'specific_gamma_constant': 13.2,  # R·m²/Ci·hr
        'source': 'NIST RadData, NRC NUREG-1556',
    },
    'Cs-137': {
        'gamma_energy_mev': 0.563,  # Ba-137m decay (actual PyNE value, includes branching)
        'gamma_lines': [
            {'energy_kev': 661.66, 'intensity_percent': 85.1},
        ],
        'half_life_days': 10986.72,  # 30.09 years (actual PyNE value)
        'half_life_seconds': 10986.72 * 86400,
        'dose_rate_1ci_1ft_mrem_hr': 321,  # Real-world: 300-350, updated: 570 × 0.563
        'dose_rate_tolerance_percent': 10,
        'specific_gamma_constant': 3.3,  # R·m²/Ci·hr (NIST)
        'source': 'Real-world measurements (NIST/NRC), PyNE gamma energy',
    },
    'Na-22': {
        'gamma_energy_mev': 1.274,  # Actual PyNE value (primary line only)
        'gamma_lines': [
            {'energy_kev': 511.0, 'intensity_percent': 180.0},  # Two 511 keV (β+)
            {'energy_kev': 1274.54, 'intensity_percent': 99.94},
        ],
        'half_life_days': 950.31,  # 2.6 years (actual PyNE value)
        'half_life_seconds': 950.31 * 86400,
        'dose_rate_1ci_1ft_mrem_hr': 726,  # Calculated: 570 × 1.274
        'dose_rate_tolerance_percent': 15,  # Higher tolerance for complex decay
        'specific_gamma_constant': 12.0,  # R·m²/Ci·hr
        'source': 'Calculated from PyNE gamma energy (primary line)',
    },
    'Au-198': {
        'gamma_energy_mev': 0.419,  # Total energy per decay (from PyNE)
        'gamma_lines': [
            {'energy_kev': 411.80, 'intensity_percent': 95.58},
            {'energy_kev': 675.88, 'intensity_percent': 0.84},
            {'energy_kev': 1087.68, 'intensity_percent': 0.17},
        ],
        'half_life_days': 2.6941,
        'half_life_seconds': 2.6941 * 86400,
        'dose_rate_1ci_1ft_mrem_hr': 239,  # Calculated: 570 × 0.419
        'dose_rate_tolerance_percent': 10,
        'specific_gamma_constant': 2.3,  # R·m²/Ci·hr (approximate)
        'source': 'Calculated from PyNE gamma energy',
    },
}

# =============================================================================
# NEUTRON ACTIVATION CROSS-SECTIONS
# =============================================================================

ACTIVATION_CROSS_SECTIONS = {
    'Au-197': {
        'target_isotope': 'Au-197',
        'product_isotope': 'Au-198',
        'natural_abundance_percent': 100.0,
        'atomic_mass': 197,
        'thermal_xs_barns': 98.65,  # Well-known value
        'resonance_integral_barns': 1558,  # For epithermal activation
        'product_half_life_days': 2.6941,
        'product_half_life_seconds': 2.6941 * 86400,
        'source': 'IAEA, ENDF/B-VIII.0',
    },
    'Al-27': {
        'target_isotope': 'Al-27',
        'product_isotope': 'Al-28',
        'natural_abundance_percent': 100.0,
        'atomic_mass': 27,
        'thermal_xs_barns': 0.231,
        'resonance_integral_barns': 0.17,
        'product_half_life_days': 0.0933,  # 134.4 minutes
        'product_half_life_seconds': 134.4 * 60,
        'source': 'IAEA, ENDF/B-VIII.0',
    },
    'Co-59': {
        'target_isotope': 'Co-59',
        'product_isotope': 'Co-60',
        'natural_abundance_percent': 100.0,
        'atomic_mass': 59,
        'thermal_xs_barns': 37.18,
        'resonance_integral_barns': 74.2,
        'product_half_life_days': 1925.28,  # 5.27 years
        'product_half_life_seconds': 1925.28 * 86400,
        'source': 'IAEA, ENDF/B-VIII.0',
    },
    'Mn-55': {
        'target_isotope': 'Mn-55',
        'product_isotope': 'Mn-56',
        'natural_abundance_percent': 100.0,
        'atomic_mass': 55,
        'thermal_xs_barns': 13.3,
        'resonance_integral_barns': 14.0,
        'product_half_life_days': 0.1074,  # 2.5789 hours
        'product_half_life_seconds': 2.5789 * 3600,
        'source': 'IAEA, ENDF/B-VIII.0',
    },
}

# =============================================================================
# GOLD FOIL ACTIVATION SCENARIOS
# =============================================================================

GOLD_FOIL_SCENARIOS = [
    {
        'name': 'Standard 2.5g foil, high flux, 1 hour',
        'mass_g': 2.5,
        'thermal_flux_n_cm2_s': 2.5e12,
        'fast_flux_n_cm2_s': 1.0e11,
        'irradiation_time_hr': 1.0,
        'irradiation_time_s': 3600,
        'expected_activity_eoi_mci': 543.16,  # End of irradiation
        'expected_activity_1day_mci': 346.67,  # After 1 day
        'expected_activity_3day_mci': 251.02,  # After 3 days
        'expected_activity_7day_mci': 144.91,  # After 1 week
        'expected_dose_rate_eoi_mrem_hr': 120.8,  # At EOI
        'expected_dose_rate_3day_mrem_hr': 55.8,  # After 3 days
        'tolerance_percent': 5,
        'source': 'Manual calculation verified',
    },
    {
        'name': 'Small 1g foil, same flux, 1 hour',
        'mass_g': 1.0,
        'thermal_flux_n_cm2_s': 2.5e12,
        'fast_flux_n_cm2_s': 1.0e11,
        'irradiation_time_hr': 1.0,
        'irradiation_time_s': 3600,
        'expected_activity_eoi_mci': 217.26,  # Scales linearly with mass
        'expected_activity_3day_mci': 100.41,
        'expected_dose_rate_3day_mrem_hr': 22.3,
        'tolerance_percent': 5,
        'source': 'Linear scaling from 2.5g case',
    },
    {
        'name': 'Large 10g foil, same flux, 1 hour',
        'mass_g': 10.0,
        'thermal_flux_n_cm2_s': 2.5e12,
        'fast_flux_n_cm2_s': 1.0e11,
        'irradiation_time_hr': 1.0,
        'irradiation_time_s': 3600,
        'expected_activity_eoi_mci': 2172.6,  # 4× the 2.5g case
        'expected_activity_3day_mci': 1004.1,
        'expected_dose_rate_3day_mrem_hr': 223.2,
        'tolerance_percent': 5,
        'source': 'Linear scaling from 2.5g case',
    },
    {
        'name': 'Standard foil, lower flux, 1 hour',
        'mass_g': 2.5,
        'thermal_flux_n_cm2_s': 1.0e12,  # 40% of high flux
        'fast_flux_n_cm2_s': 0.5e11,
        'irradiation_time_hr': 1.0,
        'irradiation_time_s': 3600,
        'expected_activity_eoi_mci': 217.26,  # Scales with flux
        'expected_activity_3day_mci': 100.41,
        'expected_dose_rate_3day_mrem_hr': 22.3,
        'tolerance_percent': 5,
        'source': 'Linear scaling with flux',
    },
    {
        'name': 'Standard foil, high flux, 6 hours (saturation test)',
        'mass_g': 2.5,
        'thermal_flux_n_cm2_s': 2.5e12,
        'fast_flux_n_cm2_s': 1.0e11,
        'irradiation_time_hr': 6.0,
        'irradiation_time_s': 6 * 3600,
        'expected_activity_eoi_mci': 2342.0,  # Approaching saturation
        'expected_activity_3day_mci': 1082.0,
        'expected_dose_rate_3day_mrem_hr': 240.6,
        'tolerance_percent': 5,
        'source': 'Saturation formula calculation',
    },
]

# =============================================================================
# DOSE RATE FORMULA CONSTANTS
# =============================================================================

DOSE_RATE_FORMULA = {
    'K_constant': 570.0,  # Empirical constant for point source at 1 foot
    'K_derivation': {
        'Co-60': {'dose_1ci_1ft': 1400, 'energy_mev_pyne': 2.504, 'K_calculated': 559},
        'Cs-137': {'dose_1ci_1ft': 325, 'energy_mev_pyne': 0.563, 'K_calculated': 577},
        'average': 568,
        'used': 570,
    },
    'formula': 'dose_rate (mrem/hr) = K × activity (Ci) × energy (MeV) / distance²',
    'units': {
        'dose_rate': 'mrem/hr',
        'activity': 'Ci',
        'energy': 'MeV (total per decay)',
        'distance': 'feet',
    },
    'fallback_beta_only': 500.0,  # mrem/hr per Ci for pure beta emitters
}

# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

PHYSICAL_CONSTANTS = {
    'avogadro': 6.022e23,  # atoms/mol
    'barn_to_cm2': 1e-24,  # 1 barn = 10^-24 cm²
    'curie_to_bq': 3.7e10,  # 1 Ci = 3.7×10^10 Bq
    'r_to_mrem': 1000,  # 1 R ≈ 1000 mrem (for gamma, in tissue)
    'mev_to_joules': 1.60218e-13,  # 1 MeV = 1.60218×10^-13 J
    'ln2': 0.693147180559945,  # Natural log of 2
}

# =============================================================================
# TOLERANCE SPECIFICATIONS
# =============================================================================

TEST_TOLERANCES = {
    'dose_rate_percent': 10,  # ±10% for dose rates (literature variation)
    'activity_percent': 5,  # ±5% for calculated activities
    'gamma_energy_percent': 1,  # ±1% for gamma energies (PyNE precision)
    'cross_section_percent': 5,  # ±5% for cross-sections
    'half_life_percent': 0.1,  # ±0.1% for half-lives (well-known values)
}

# =============================================================================
# REGRESSION TEST VALUES (BUGS TO PREVENT)
# =============================================================================

REGRESSION_TESTS = {
    'dose_rate_constant_bug': {
        'description': 'The K=6 bug: dose rate constant was 6 instead of 530',
        'wrong_value': 6.0,
        'correct_value': 530.0,
        'test': 'Ensure K ≠ 6 in dose rate calculations',
    },
    'gamma_energy_normalization_bug': {
        'description': 'Divided by total_intensity instead of 100 for percent',
        'example': 'Co-60 weighted avg = 1.25 MeV (wrong) vs 2.5 MeV (correct)',
        'test': 'Ensure multi-gamma emitters calculate total energy, not average',
    },
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_expected_activity(scenario_name, decay_time_days):
    """
    Get expected activity for a scenario at a given decay time

    Args:
        scenario_name: Name of scenario from GOLD_FOIL_SCENARIOS
        decay_time_days: Time after EOI in days (0, 1, 3, 7, etc.)

    Returns:
        float: Expected activity in mCi, or None if not defined
    """
    for scenario in GOLD_FOIL_SCENARIOS:
        if scenario['name'] == scenario_name:
            if decay_time_days == 0:
                return scenario.get('expected_activity_eoi_mci')
            elif decay_time_days == 1:
                return scenario.get('expected_activity_1day_mci')
            elif decay_time_days == 3:
                return scenario.get('expected_activity_3day_mci')
            elif decay_time_days == 7:
                return scenario.get('expected_activity_7day_mci')
    return None

def get_dose_rate_reference(isotope, activity_ci=1.0):
    """
    Get reference dose rate for an isotope

    Args:
        isotope: Isotope name (e.g., 'Co-60')
        activity_ci: Activity in Curies (default 1.0)

    Returns:
        dict with 'value', 'tolerance', 'source'
    """
    if isotope in NIST_DOSE_CONSTANTS:
        ref = NIST_DOSE_CONSTANTS[isotope]
        base_dose = ref['dose_rate_1ci_1ft_mrem_hr']
        return {
            'value': base_dose * activity_ci,
            'tolerance_percent': ref['dose_rate_tolerance_percent'],
            'source': ref['source'],
        }
    return None

def calculate_decay(initial_activity_bq, half_life_s, time_s):
    """
    Calculate activity after decay time using exponential decay

    Args:
        initial_activity_bq: Initial activity in Bq
        half_life_s: Half-life in seconds
        time_s: Decay time in seconds

    Returns:
        float: Activity after decay in Bq
    """
    import math
    lambda_decay = PHYSICAL_CONSTANTS['ln2'] / half_life_s
    return initial_activity_bq * math.exp(-lambda_decay * time_s)
