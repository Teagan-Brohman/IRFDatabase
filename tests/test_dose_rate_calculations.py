"""
Unit tests for dose rate calculations

Tests the dose rate estimation formula against NIST/NRC reference data
for common calibration sources (Co-60, Cs-137, Na-22, Au-198).

Validates:
- Dose rate constant K ≈ 530
- Gamma energy calculations
- Point source formula at 1 foot
- Regression tests (prevent K=6 bug)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from django.test import TestCase
from decimal import Decimal
import math

from irradiation.activation import ActivationCalculator
from tests.fixtures.reference_data import (
    NIST_DOSE_CONSTANTS,
    DOSE_RATE_FORMULA,
    TEST_TOLERANCES,
    REGRESSION_TESTS,
    PHYSICAL_CONSTANTS,
)


class DoseRateFormulaTests(TestCase):
    """Test the dose rate formula and constants"""

    def setUp(self):
        """Initialize calculator for all tests"""
        self.calc = ActivationCalculator(use_multigroup=False)
        self.K = DOSE_RATE_FORMULA['K_constant']

    def test_dose_rate_constant_is_530(self):
        """Test that K constant is 530, not 6 (regression test)"""
        # This prevents the K=6 bug from returning
        wrong_K = REGRESSION_TESTS['dose_rate_constant_bug']['wrong_value']
        correct_K = REGRESSION_TESTS['dose_rate_constant_bug']['correct_value']

        self.assertEqual(self.K, correct_K,
                        f"K should be {correct_K}, not {wrong_K}")
        self.assertNotEqual(self.K, wrong_K,
                           "Regression: K=6 bug detected!")

    def test_dose_rate_formula_structure(self):
        """Test that dose rate formula has correct structure"""
        # Verify formula constants exist
        self.assertIn('K_constant', DOSE_RATE_FORMULA)
        self.assertIn('formula', DOSE_RATE_FORMULA)
        self.assertIn('units', DOSE_RATE_FORMULA)

        # Verify K is in reasonable range (not the old bug value of 6)
        self.assertGreater(self.K, 100, "K seems too small")
        self.assertLess(self.K, 1000, "K seems too large")


class GammaEnergyCalculationTests(TestCase):
    """Test gamma energy calculations from PyNE data"""

    def setUp(self):
        """Initialize calculator"""
        self.calc = ActivationCalculator(use_multigroup=False)

    def test_co60_gamma_energy(self):
        """Test Co-60 gamma energy (2 gammas: 1.17 + 1.33 MeV)"""
        expected = NIST_DOSE_CONSTANTS['Co-60']['gamma_energy_mev']
        tolerance = TEST_TOLERANCES['gamma_energy_percent'] / 100.0

        gamma_energy = self.calc._get_gamma_energies('Co-60')

        self.assertIsNotNone(gamma_energy, "Co-60 gamma energy should not be None")
        self.assertAlmostEqual(gamma_energy, expected, delta=expected * tolerance,
                              msg=f"Co-60 gamma energy should be ~{expected} MeV")

    def test_cs137_gamma_energy(self):
        """Test Cs-137 gamma energy (single 662 keV gamma)"""
        expected = NIST_DOSE_CONSTANTS['Cs-137']['gamma_energy_mev']
        tolerance = TEST_TOLERANCES['gamma_energy_percent'] / 100.0

        gamma_energy = self.calc._get_gamma_energies('Cs-137')

        self.assertIsNotNone(gamma_energy, "Cs-137 gamma energy should not be None")
        self.assertAlmostEqual(gamma_energy, expected, delta=expected * tolerance,
                              msg=f"Cs-137 gamma energy should be ~{expected} MeV")

    def test_na22_gamma_energy(self):
        """Test Na-22 gamma energy (2×511 + 1275 keV)"""
        expected = NIST_DOSE_CONSTANTS['Na-22']['gamma_energy_mev']
        tolerance = TEST_TOLERANCES['gamma_energy_percent'] / 100.0 * 2  # More tolerance for complex decay

        gamma_energy = self.calc._get_gamma_energies('Na-22')

        self.assertIsNotNone(gamma_energy, "Na-22 gamma energy should not be None")
        self.assertAlmostEqual(gamma_energy, expected, delta=expected * tolerance,
                              msg=f"Na-22 gamma energy should be ~{expected} MeV")

    def test_au198_gamma_energy(self):
        """Test Au-198 gamma energy (411 keV primary)"""
        expected = NIST_DOSE_CONSTANTS['Au-198']['gamma_energy_mev']
        tolerance = TEST_TOLERANCES['gamma_energy_percent'] / 100.0

        gamma_energy = self.calc._get_gamma_energies('Au-198')

        self.assertIsNotNone(gamma_energy, "Au-198 gamma energy should not be None")
        self.assertAlmostEqual(gamma_energy, expected, delta=expected * tolerance,
                              msg=f"Au-198 gamma energy should be ~{expected} MeV")

    def test_multi_gamma_emitter_not_averaged(self):
        """
        Regression test: Ensure multi-gamma emitters calculate TOTAL energy,
        not weighted average (the old bug)
        """
        # Co-60 emits 2 gammas with total energy ~2.5 MeV
        # Old bug would give weighted average ~1.25 MeV
        gamma_energy = self.calc._get_gamma_energies('Co-60')

        # If this is close to 1.25, the old bug has returned
        self.assertGreater(gamma_energy, 2.0,
                          "Co-60 energy too low - weighted average bug detected!")
        self.assertLess(gamma_energy, 3.0,
                       "Co-60 energy too high")


class DoseRateNISTValidationTests(TestCase):
    """Validate dose rate calculations against NIST reference data"""

    def setUp(self):
        """Initialize calculator"""
        self.calc = ActivationCalculator(use_multigroup=False)

    def _create_isotope_dict(self, isotope_name, activity_ci):
        """Helper to create isotope dictionary for testing"""
        return {
            isotope_name: {
                'activity_ci': activity_ci,
                'activity_bq': activity_ci * PHYSICAL_CONSTANTS['curie_to_bq'],
            }
        }

    def test_co60_1ci_1ft_dose_rate(self):
        """Test Co-60: 1 Ci at 1 foot = 1300-1500 mrem/hr (NIST)"""
        ref_data = NIST_DOSE_CONSTANTS['Co-60']
        expected = ref_data['dose_rate_1ci_1ft_mrem_hr']
        tolerance_pct = ref_data['dose_rate_tolerance_percent']

        isotopes = self._create_isotope_dict('Co-60', 1.0)
        dose_rate = self.calc._estimate_dose_rate(isotopes)

        delta = expected * (tolerance_pct / 100.0)
        self.assertAlmostEqual(dose_rate, expected, delta=delta,
                              msg=f"Co-60 dose rate should be {expected} ± {tolerance_pct}% mrem/hr")

    def test_cs137_1ci_1ft_dose_rate(self):
        """Test Cs-137: 1 Ci at 1 foot = ~330 mrem/hr (NIST)"""
        ref_data = NIST_DOSE_CONSTANTS['Cs-137']
        expected = ref_data['dose_rate_1ci_1ft_mrem_hr']
        tolerance_pct = ref_data['dose_rate_tolerance_percent']

        isotopes = self._create_isotope_dict('Cs-137', 1.0)
        dose_rate = self.calc._estimate_dose_rate(isotopes)

        delta = expected * (tolerance_pct / 100.0)
        self.assertAlmostEqual(dose_rate, expected, delta=delta,
                              msg=f"Cs-137 dose rate should be {expected} ± {tolerance_pct}% mrem/hr")

    def test_na22_1ci_1ft_dose_rate(self):
        """Test Na-22: 1 Ci at 1 foot = ~1200 mrem/hr (reference)"""
        ref_data = NIST_DOSE_CONSTANTS['Na-22']
        expected = ref_data['dose_rate_1ci_1ft_mrem_hr']
        tolerance_pct = ref_data['dose_rate_tolerance_percent']

        isotopes = self._create_isotope_dict('Na-22', 1.0)
        dose_rate = self.calc._estimate_dose_rate(isotopes)

        delta = expected * (tolerance_pct / 100.0)
        self.assertAlmostEqual(dose_rate, expected, delta=delta,
                              msg=f"Na-22 dose rate should be {expected} ± {tolerance_pct}% mrem/hr")

    def test_au198_1ci_1ft_dose_rate(self):
        """Test Au-198: 1 Ci at 1 foot = ~220 mrem/hr (calculated)"""
        ref_data = NIST_DOSE_CONSTANTS['Au-198']
        expected = ref_data['dose_rate_1ci_1ft_mrem_hr']
        tolerance_pct = ref_data['dose_rate_tolerance_percent']

        isotopes = self._create_isotope_dict('Au-198', 1.0)
        dose_rate = self.calc._estimate_dose_rate(isotopes)

        delta = expected * (tolerance_pct / 100.0)
        self.assertAlmostEqual(dose_rate, expected, delta=delta,
                              msg=f"Au-198 dose rate should be {expected} ± {tolerance_pct}% mrem/hr")


class DoseRateScalingTests(TestCase):
    """Test dose rate scaling with activity"""

    def setUp(self):
        """Initialize calculator"""
        self.calc = ActivationCalculator(use_multigroup=False)

    def _create_isotope_dict(self, isotope_name, activity_ci):
        """Helper to create isotope dictionary"""
        return {
            isotope_name: {
                'activity_ci': activity_ci,
                'activity_bq': activity_ci * PHYSICAL_CONSTANTS['curie_to_bq'],
            }
        }

    def test_dose_rate_scales_linearly_with_activity(self):
        """Test that dose rate scales linearly with activity"""
        # Test with Co-60
        isotopes_1ci = self._create_isotope_dict('Co-60', 1.0)
        isotopes_10ci = self._create_isotope_dict('Co-60', 10.0)

        dose_1ci = self.calc._estimate_dose_rate(isotopes_1ci)
        dose_10ci = self.calc._estimate_dose_rate(isotopes_10ci)

        # Should be exactly 10× (within floating point precision)
        ratio = dose_10ci / dose_1ci
        self.assertAlmostEqual(ratio, 10.0, delta=0.01,
                              msg="Dose rate should scale linearly with activity")

    def test_small_activity_dose_rate(self):
        """Test dose rate with small activity (mCi range)"""
        # 100 mCi of Au-198
        activity_ci = 0.1
        isotopes = self._create_isotope_dict('Au-198', activity_ci)

        dose_rate = self.calc._estimate_dose_rate(isotopes)

        # Should be ~22 mrem/hr (220 mrem/hr × 0.1)
        expected = 22.0
        self.assertAlmostEqual(dose_rate, expected, delta=2.0,
                              msg=f"100 mCi Au-198 should give ~{expected} mrem/hr")

    def test_large_activity_dose_rate(self):
        """Test dose rate with large activity (multi-Ci)"""
        # 100 Ci of Cs-137 (large source)
        activity_ci = 100.0
        isotopes = self._create_isotope_dict('Cs-137', activity_ci)

        dose_rate = self.calc._estimate_dose_rate(isotopes)

        # Should be ~33,000 mrem/hr (330 × 100)
        expected = 33000.0
        self.assertAlmostEqual(dose_rate, expected, delta=3000.0,
                              msg=f"100 Ci Cs-137 should give ~{expected} mrem/hr")


class MultiIsotopeDoseRateTests(TestCase):
    """Test dose rate calculations with multiple isotopes"""

    def setUp(self):
        """Initialize calculator"""
        self.calc = ActivationCalculator(use_multigroup=False)

    def test_two_isotope_mixture(self):
        """Test dose rate from mixture of Co-60 and Cs-137"""
        isotopes = {
            'Co-60': {
                'activity_ci': 1.0,
                'activity_bq': 3.7e10,
            },
            'Cs-137': {
                'activity_ci': 1.0,
                'activity_bq': 3.7e10,
            },
        }

        total_dose = self.calc._estimate_dose_rate(isotopes)

        # Should be sum: 1400 + 330 = 1730 mrem/hr
        expected = 1730.0
        self.assertAlmostEqual(total_dose, expected, delta=200.0,
                              msg="Multi-isotope dose should be sum of individual doses")

    def test_mixture_ratios(self):
        """Test dose rate with different activity ratios"""
        # 10 Ci Co-60 + 1 Ci Cs-137
        isotopes = {
            'Co-60': {'activity_ci': 10.0, 'activity_bq': 10 * 3.7e10},
            'Cs-137': {'activity_ci': 1.0, 'activity_bq': 3.7e10},
        }

        total_dose = self.calc._estimate_dose_rate(isotopes)

        # Should be: 10×1400 + 1×330 = 14,330 mrem/hr
        expected = 14330.0
        self.assertAlmostEqual(total_dose, expected, delta=1500.0,
                              msg="Dose should account for activity ratios")


if __name__ == '__main__':
    import unittest
    unittest.main()
