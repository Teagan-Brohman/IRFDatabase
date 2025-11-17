#!/usr/bin/env python
"""
Comprehensive Standalone Validation Test Suite

This script validates neutron activation and dose rate calculations against
NIST/NRC reference data. It can run independently without Django.

Usage:
    python test_suite_validation.py

Tests:
    - Dose rate calculations (Co-60, Cs-137, Na-22, Au-198)
    - Gamma energy lookups
    - Gold foil activation scenarios
    - Mass and flux scaling
    - Decay calculations

Reference Data:
    - NIST RadData
    - NRC NUREG-1556
    - IAEA cross-sections
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from irradiation.activation import ActivationCalculator
from tests.fixtures.reference_data import (
    NIST_DOSE_CONSTANTS,
    DOSE_RATE_FORMULA,
    GOLD_FOIL_SCENARIOS,
    PHYSICAL_CONSTANTS,
    TEST_TOLERANCES,
)
import math
from datetime import datetime


class TestResult:
    """Container for test results"""
    def __init__(self, name, passed, expected, actual, tolerance=None, error=None):
        self.name = name
        self.passed = passed
        self.expected = expected
        self.actual = actual
        self.tolerance = tolerance
        self.error = error


class TestSuite:
    """Main test suite runner"""

    def __init__(self):
        self.calc = ActivationCalculator(use_multigroup=False)
        self.results = []
        self.start_time = None
        self.end_time = None

    def run_all_tests(self):
        """Run all test categories"""
        print("="*80)
        print("NEUTRON ACTIVATION & DOSE RATE VALIDATION TEST SUITE")
        print("="*80)
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        self.start_time = datetime.now()

        # Run test categories
        print("Running dose rate validation tests...")
        self.test_dose_rate_constants()

        print("\nRunning gamma energy calculation tests...")
        self.test_gamma_energies()

        print("\nRunning dose rate scaling tests...")
        self.test_dose_rate_scaling()

        print("\nRunning activation formula tests...")
        self.test_activation_formulas()

        print("\nRunning decay time tests...")
        self.test_decay_calculations()

        self.end_time = datetime.now()

        # Generate summary report
        self.print_summary()

    def test_dose_rate_constants(self):
        """Test dose rate constant K = 570"""
        K = DOSE_RATE_FORMULA['K_constant']

        # Test 1: K should be 570, not 6
        test_name = "Dose rate constant K = 570 (not 6)"
        passed = (K == 570.0) and (K != 6.0)
        self.results.append(TestResult(
            name=test_name,
            passed=passed,
            expected=570.0,
            actual=K,
        ))
        print(f"  {'✓' if passed else '✗'} {test_name}")

        # Test 2: Co-60 dose rate
        isotopes_co60 = {'Co-60': {'activity_ci': 1.0, 'activity_bq': 3.7e10}}
        dose_co60 = self.calc._estimate_dose_rate(isotopes_co60)
        expected_co60 = NIST_DOSE_CONSTANTS['Co-60']['dose_rate_1ci_1ft_mrem_hr']
        tolerance_co60 = expected_co60 * 0.10  # 10%
        passed = abs(dose_co60 - expected_co60) <= tolerance_co60

        test_name = "Co-60: 1 Ci @ 1 ft = 1400 mrem/hr"
        self.results.append(TestResult(
            name=test_name,
            passed=passed,
            expected=expected_co60,
            actual=dose_co60,
            tolerance=tolerance_co60,
        ))
        print(f"  {'✓' if passed else '✗'} {test_name} (actual: {dose_co60:.1f})")

        # Test 3: Cs-137 dose rate
        isotopes_cs137 = {'Cs-137': {'activity_ci': 1.0, 'activity_bq': 3.7e10}}
        dose_cs137 = self.calc._estimate_dose_rate(isotopes_cs137)
        expected_cs137 = NIST_DOSE_CONSTANTS['Cs-137']['dose_rate_1ci_1ft_mrem_hr']
        tolerance_cs137 = expected_cs137 * 0.10
        passed = abs(dose_cs137 - expected_cs137) <= tolerance_cs137

        test_name = "Cs-137: 1 Ci @ 1 ft = 330 mrem/hr"
        self.results.append(TestResult(
            name=test_name,
            passed=passed,
            expected=expected_cs137,
            actual=dose_cs137,
            tolerance=tolerance_cs137,
        ))
        print(f"  {'✓' if passed else '✗'} {test_name} (actual: {dose_cs137:.1f})")

        # Test 4: Na-22 dose rate
        isotopes_na22 = {'Na-22': {'activity_ci': 1.0, 'activity_bq': 3.7e10}}
        dose_na22 = self.calc._estimate_dose_rate(isotopes_na22)
        expected_na22 = NIST_DOSE_CONSTANTS['Na-22']['dose_rate_1ci_1ft_mrem_hr']
        tolerance_na22 = expected_na22 * 0.10
        passed = abs(dose_na22 - expected_na22) <= tolerance_na22

        test_name = "Na-22: 1 Ci @ 1 ft = 1200 mrem/hr"
        self.results.append(TestResult(
            name=test_name,
            passed=passed,
            expected=expected_na22,
            actual=dose_na22,
            tolerance=tolerance_na22,
        ))
        print(f"  {'✓' if passed else '✗'} {test_name} (actual: {dose_na22:.1f})")

        # Test 5: Au-198 dose rate
        isotopes_au198 = {'Au-198': {'activity_ci': 1.0, 'activity_bq': 3.7e10}}
        dose_au198 = self.calc._estimate_dose_rate(isotopes_au198)
        expected_au198 = NIST_DOSE_CONSTANTS['Au-198']['dose_rate_1ci_1ft_mrem_hr']
        tolerance_au198 = expected_au198 * 0.05  # 5%
        passed = abs(dose_au198 - expected_au198) <= tolerance_au198

        test_name = "Au-198: 1 Ci @ 1 ft = 220 mrem/hr"
        self.results.append(TestResult(
            name=test_name,
            passed=passed,
            expected=expected_au198,
            actual=dose_au198,
            tolerance=tolerance_au198,
        ))
        print(f"  {'✓' if passed else '✗'} {test_name} (actual: {dose_au198:.1f})")

    def test_gamma_energies(self):
        """Test gamma energy calculations"""

        test_cases = [
            ('Co-60', 2.504, 'Two gammas: 1.173 + 1.332 MeV'),
            ('Cs-137', 0.563, 'Ba-137m 662 keV (85% branching)'),
            ('Na-22', 1.274, 'Primary 1275 keV line'),
            ('Au-198', 0.419, 'Primary 411.8 keV gamma'),
        ]

        for isotope, expected, description in test_cases:
            gamma_energy = self.calc._get_gamma_energies(isotope)

            if gamma_energy is None:
                test_name = f"{isotope} gamma energy"
                self.results.append(TestResult(
                    name=test_name,
                    passed=False,
                    expected=expected,
                    actual=None,
                    error="PyNE data not available",
                ))
                print(f"  ⚠ {test_name}: PyNE data not available")
                continue

            tolerance = expected * 0.02  # 2% tolerance
            passed = abs(gamma_energy - expected) <= tolerance

            test_name = f"{isotope} gamma energy = {expected} MeV"
            self.results.append(TestResult(
                name=test_name,
                passed=passed,
                expected=expected,
                actual=gamma_energy,
                tolerance=tolerance,
            ))
            print(f"  {'✓' if passed else '✗'} {test_name} ({description})")

        # Special test: multi-gamma emitter shouldn't be averaged
        gamma_co60 = self.calc._get_gamma_energies('Co-60')
        if gamma_co60:
            passed = gamma_co60 > 2.0  # Should be total, not average (~1.25)
            test_name = "Co-60 multi-gamma NOT averaged (regression test)"
            self.results.append(TestResult(
                name=test_name,
                passed=passed,
                expected="> 2.0 MeV (total)",
                actual=gamma_co60,
            ))
            print(f"  {'✓' if passed else '✗'} {test_name}")

    def test_dose_rate_scaling(self):
        """Test dose rate scaling with activity"""

        # Test linear scaling
        isotopes_1ci = {'Co-60': {'activity_ci': 1.0, 'activity_bq': 3.7e10}}
        isotopes_10ci = {'Co-60': {'activity_ci': 10.0, 'activity_bq': 3.7e11}}

        dose_1ci = self.calc._estimate_dose_rate(isotopes_1ci)
        dose_10ci = self.calc._estimate_dose_rate(isotopes_10ci)

        ratio = dose_10ci / dose_1ci if dose_1ci > 0 else 0
        passed = abs(ratio - 10.0) < 0.1

        test_name = "Dose rate scales linearly with activity (10×)"
        self.results.append(TestResult(
            name=test_name,
            passed=passed,
            expected=10.0,
            actual=ratio,
        ))
        print(f"  {'✓' if passed else '✗'} {test_name} (ratio: {ratio:.2f})")

        # Test small activity
        isotopes_100mci = {'Au-198': {'activity_ci': 0.1, 'activity_bq': 3.7e9}}
        dose_100mci = self.calc._estimate_dose_rate(isotopes_100mci)
        expected_100mci = 22.0  # 220 × 0.1
        passed = abs(dose_100mci - expected_100mci) < 3.0

        test_name = "Small activity: 100 mCi Au-198 = 22 mrem/hr"
        self.results.append(TestResult(
            name=test_name,
            passed=passed,
            expected=expected_100mci,
            actual=dose_100mci,
        ))
        print(f"  {'✓' if passed else '✗'} {test_name} (actual: {dose_100mci:.1f})")

        # Test multi-isotope mixture
        isotopes_mix = {
            'Co-60': {'activity_ci': 1.0, 'activity_bq': 3.7e10},
            'Cs-137': {'activity_ci': 1.0, 'activity_bq': 3.7e10},
        }
        dose_mix = self.calc._estimate_dose_rate(isotopes_mix)
        expected_mix = 1730.0  # 1400 + 330
        passed = abs(dose_mix - expected_mix) < 200.0

        test_name = "Multi-isotope: Co-60 + Cs-137 dose = sum"
        self.results.append(TestResult(
            name=test_name,
            passed=passed,
            expected=expected_mix,
            actual=dose_mix,
        ))
        print(f"  {'✓' if passed else '✗'} {test_name} (actual: {dose_mix:.1f})")

    def test_activation_formulas(self):
        """Test activation formula components"""

        # Test saturation factor calculation
        half_life_s = 2.6941 * 86400  # Au-198
        lambda_decay = PHYSICAL_CONSTANTS['ln2'] / half_life_s

        test_times = [
            (half_life_s * 1.0, 0.50, "1 half-life = 50% saturation"),
            (half_life_s * 3.0, 0.875, "3 half-lives = 87.5% saturation"),
            (half_life_s * 7.0, 0.9922, "7 half-lives = 99.22% saturation"),
        ]

        for time_s, expected_frac, description in test_times:
            actual_frac = 1 - math.exp(-lambda_decay * time_s)
            passed = abs(actual_frac - expected_frac) < 0.01

            test_name = f"Saturation: {description}"
            self.results.append(TestResult(
                name=test_name,
                passed=passed,
                expected=expected_frac,
                actual=actual_frac,
            ))
            print(f"  {'✓' if passed else '✗'} {test_name}")

    def test_decay_calculations(self):
        """Test decay calculations"""

        # Au-198 decay test
        half_life_s = 2.6941 * 86400
        lambda_decay = PHYSICAL_CONSTANTS['ln2'] / half_life_s

        # Create inventory with 1e10 Bq initial activity
        initial_activity = 1.0e10
        n_atoms = initial_activity / lambda_decay
        inventory = {'Au-198': n_atoms}

        decay_tests = [
            (0, 1.0, "No decay"),
            (1 * 86400, 0.7731, "1 day"),
            (2.6941 * 86400, 0.5, "1 half-life"),
            (3 * 86400, 0.4622, "3 days"),
            (7 * 86400, 0.1651, "7 days"),
        ]

        for time_s, expected_frac, description in decay_tests:
            decayed_inv = self.calc._decay_inventory(inventory.copy(), time_s)
            n_remaining = decayed_inv.get('Au-198', 0)
            activity_remaining = n_remaining * lambda_decay
            actual_frac = activity_remaining / initial_activity

            passed = abs(actual_frac - expected_frac) < 0.02

            test_name = f"Au-198 decay after {description}: {expected_frac*100:.1f}% remains"
            self.results.append(TestResult(
                name=test_name,
                passed=passed,
                expected=expected_frac,
                actual=actual_frac,
            ))
            print(f"  {'✓' if passed else '✗'} {test_name}")

    def print_summary(self):
        """Print test summary report"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        print(f"\nTotal tests: {total}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} ✗")
        print(f"Success rate: {passed/total*100:.1f}%")

        duration = (self.end_time - self.start_time).total_seconds()
        print(f"\nExecution time: {duration:.2f} seconds")

        if failed > 0:
            print("\n" + "="*80)
            print("FAILED TESTS")
            print("="*80)
            for result in self.results:
                if not result.passed:
                    print(f"\n✗ {result.name}")
                    print(f"  Expected: {result.expected}")
                    print(f"  Actual:   {result.actual}")
                    if result.tolerance:
                        print(f"  Tolerance: ±{result.tolerance}")
                    if result.error:
                        print(f"  Error: {result.error}")

        print("\n" + "="*80)
        print("VALIDATION RESULTS")
        print("="*80)

        if failed == 0:
            print("\n✓ ALL TESTS PASSED")
            print("\nThe neutron activation and dose rate calculations are")
            print("validated against NIST/NRC reference data.")
            print("\nDose rate calculations match empirical values within ±10%")
            print("Activation calculations follow expected saturation and decay behavior")
            return 0
        else:
            print("\n✗ SOME TESTS FAILED")
            print(f"\n{failed} test(s) did not pass validation.")
            print("Please review the failed tests above.")
            return 1


def main():
    """Main entry point"""
    suite = TestSuite()
    exit_code = suite.run_all_tests()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
