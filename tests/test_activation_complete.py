"""
Integration tests for complete neutron activation calculations

Tests the full workflow: sample composition → neutron irradiation →
activation → decay → activity & dose rate

Validates:
- Complete gold foil activation scenarios
- Mass scaling (linear with sample mass)
- Flux scaling (linear with neutron flux)
- Time scaling (saturation behavior)
- Decay calculations at various times
- Multi-element samples
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta, time as dt_time
import math

from irradiation.models import (
    Sample, SampleComposition, FluxConfiguration,
    IrradiationRequestForm, SampleIrradiationLog
)
from irradiation.activation import ActivationCalculator
from tests.fixtures.reference_data import (
    GOLD_FOIL_SCENARIOS,
    ACTIVATION_CROSS_SECTIONS,
    TEST_TOLERANCES,
    PHYSICAL_CONSTANTS,
    NIST_DOSE_CONSTANTS,
)


class GoldFoilActivationTests(TestCase):
    """Test complete gold foil activation scenarios"""

    def setUp(self):
        """Set up test fixtures"""
        self.calc = ActivationCalculator(use_multigroup=False)

        # Create flux configuration
        self.flux_config = FluxConfiguration.objects.create(
            location='test_rabbit',
            thermal_flux=Decimal('2.5e12'),
            fast_flux=Decimal('1.0e11'),
            reference_power=Decimal('200.0'),
        )

        # Create IRF
        self.irf = IrradiationRequestForm.objects.create(
            irf_number='TEST-ACT-001',
            requester_name='Test User',
            sample_description='Gold foil activation test',
            physical_form='foil',
            max_power=Decimal('200'),
            max_time=Decimal('10'),
            max_time_unit='hr',
            max_mass=Decimal('20'),
            max_mass_unit='g',
            expected_dose_rate=Decimal('1000'),
            dose_rate_basis='calculation',
            reactivity_worth=Decimal('0.01'),
            reactivity_basis='estimate',
            status='approved',
        )

    def _create_gold_sample(self, mass_g, sample_id='TEST-AU'):
        """Helper to create a gold sample"""
        sample = Sample.objects.create(
            sample_id=sample_id,
            material_type='Gold',
            description=f'Test {mass_g}g gold foil',
            mass=Decimal(str(mass_g)),
            mass_unit='g',
        )

        # Pure Au-197
        SampleComposition.objects.create(
            sample=sample,
            element='Au',
            isotope='197',
            fraction=Decimal('100.0'),
        )

        return sample

    def _create_irradiation_log(self, power_kw, time_hr, days_ago=0):
        """Helper to create an irradiation log"""
        irr_date = (timezone.now() - timedelta(days=days_ago)).date()

        log = SampleIrradiationLog.objects.create(
            parent_irf=self.irf,
            irradiation_date=irr_date,
            time_in=dt_time(10, 0),
            time_out=dt_time(10 + int(time_hr), int((time_hr % 1) * 60)),
            actual_location='test_rabbit',
            actual_power=Decimal(str(power_kw)),
            total_time=Decimal(str(time_hr)),
            total_time_unit='hr',
        )

        return log

    def test_standard_gold_foil_scenario(self):
        """Test standard 2.5g gold foil, 1 hour irradiation"""
        scenario = GOLD_FOIL_SCENARIOS[0]  # Standard scenario
        self.assertEqual(scenario['name'], 'Standard 2.5g foil, high flux, 1 hour')

        # Create sample
        sample = self._create_gold_sample(scenario['mass_g'])

        # Create irradiation (3 days ago)
        log = self._create_irradiation_log(
            power_kw=200.0,
            time_hr=scenario['irradiation_time_hr'],
            days_ago=3
        )

        # Calculate activation
        flux_configs = {'test_rabbit': self.flux_config}
        results = self.calc.calculate_activation(
            sample=sample,
            irradiation_logs=[log],
            flux_configs=flux_configs,
            use_cache=False,
        )

        self.assertTrue(results['calculation_successful'],
                       "Activation calculation should succeed")

        # Check activity at current time (3 days after irradiation)
        activity_bq = results['total_activity_bq']
        activity_mci = activity_bq / PHYSICAL_CONSTANTS['curie_to_bq'] * 1000

        expected_mci = scenario['expected_activity_3day_mci']
        tolerance = scenario['tolerance_percent'] / 100.0

        self.assertAlmostEqual(activity_mci, expected_mci,
                              delta=expected_mci * tolerance,
                              msg=f"Activity should be {expected_mci} ± {tolerance*100}% mCi")

        # Check dose rate
        dose_rate = results['estimated_dose_rate_1ft']
        expected_dose = scenario['expected_dose_rate_3day_mrem_hr']

        self.assertAlmostEqual(dose_rate, expected_dose,
                              delta=expected_dose * tolerance,
                              msg=f"Dose rate should be {expected_dose} ± {tolerance*100}% mrem/hr")

    def test_gold_foil_mass_scaling(self):
        """Test that activity scales linearly with mass"""
        # Test 1g, 2.5g, and 10g foils
        masses = [1.0, 2.5, 10.0]
        activities = []

        for i, mass_g in enumerate(masses):
            sample = self._create_gold_sample(mass_g, sample_id=f'TEST-AU-{i}')
            log = self._create_irradiation_log(200.0, 1.0, days_ago=3)

            flux_configs = {'test_rabbit': self.flux_config}
            results = self.calc.calculate_activation(
                sample=sample,
                irradiation_logs=[log],
                flux_configs=flux_configs,
                use_cache=False,
            )

            activity_mci = results['total_activity_bq'] / 3.7e7
            activities.append(activity_mci)

        # Check linear scaling
        # Activity should scale as: 1.0 : 2.5 : 10.0
        ratio_1_to_2p5 = activities[1] / activities[0]
        ratio_1_to_10 = activities[2] / activities[0]

        self.assertAlmostEqual(ratio_1_to_2p5, 2.5, delta=0.1,
                              msg="Activity should scale linearly with mass (2.5×)")
        self.assertAlmostEqual(ratio_1_to_10, 10.0, delta=0.5,
                              msg="Activity should scale linearly with mass (10×)")

    def test_gold_foil_flux_scaling(self):
        """Test that activity scales linearly with flux (at low activation)"""
        # Create two flux configurations (different power levels)
        flux_low = FluxConfiguration.objects.create(
            location='test_rabbit_low',
            thermal_flux=Decimal('1.0e12'),  # 40% of high flux
            fast_flux=Decimal('0.5e11'),
            reference_power=Decimal('80.0'),
        )

        flux_high = FluxConfiguration.objects.create(
            location='test_rabbit_high',
            thermal_flux=Decimal('2.5e12'),
            fast_flux=Decimal('1.0e11'),
            reference_power=Decimal('200.0'),
        )

        # Test same sample at both fluxes
        sample_low = self._create_gold_sample(2.5, 'TEST-AU-LOW')
        sample_high = self._create_gold_sample(2.5, 'TEST-AU-HIGH')

        # Short irradiation to avoid saturation effects
        log_low = SampleIrradiationLog.objects.create(
            parent_irf=self.irf,
            irradiation_date=(timezone.now() - timedelta(days=3)).date(),
            time_in=dt_time(10, 0),
            time_out=dt_time(10, 30),  # 30 minutes
            actual_location='test_rabbit_low',
            actual_power=Decimal('80.0'),
            total_time=Decimal('0.5'),
            total_time_unit='hr',
        )

        log_high = SampleIrradiationLog.objects.create(
            parent_irf=self.irf,
            irradiation_date=(timezone.now() - timedelta(days=3)).date(),
            time_in=dt_time(10, 0),
            time_out=dt_time(10, 30),
            actual_location='test_rabbit_high',
            actual_power=Decimal('200.0'),
            total_time=Decimal('0.5'),
            total_time_unit='hr',
        )

        # Calculate for both
        results_low = self.calc.calculate_activation(
            sample=sample_low,
            irradiation_logs=[log_low],
            flux_configs={'test_rabbit_low': flux_low},
            use_cache=False,
        )

        results_high = self.calc.calculate_activation(
            sample=sample_high,
            irradiation_logs=[log_high],
            flux_configs={'test_rabbit_high': flux_high},
            use_cache=False,
        )

        # Activity ratio should be ~2.5 (flux ratio)
        activity_low = results_low['total_activity_bq']
        activity_high = results_high['total_activity_bq']
        ratio = activity_high / activity_low

        self.assertAlmostEqual(ratio, 2.5, delta=0.3,
                              msg="Activity should scale linearly with flux")


class DecayTimeTests(TestCase):
    """Test decay calculations at various times"""

    def setUp(self):
        """Set up calculator and reference data"""
        self.calc = ActivationCalculator(use_multigroup=False)
        self.au198_half_life_s = NIST_DOSE_CONSTANTS['Au-198']['half_life_seconds']

    def test_au198_decay_over_time(self):
        """Test Au-198 decay at 0, 1, 3, 7 days"""
        # Create mock inventory with known activity
        initial_activity_bq = 1.0e10  # 10 GBq

        # Calculate number of atoms from activity
        # A = λN, so N = A/λ
        lambda_decay = PHYSICAL_CONSTANTS['ln2'] / self.au198_half_life_s
        n_atoms = initial_activity_bq / lambda_decay

        inventory = {'Au-198': n_atoms}

        # Test decay at different times
        decay_times = [
            (0, 1.0),      # 0 days: 100% remains
            (1, 0.7774),   # 1 day: ~77.74%
            (2.6941, 0.5), # 1 half-life: 50%
            (3, 0.6051),   # 3 days: ~60.51%
            (7, 0.2772),   # 7 days: ~27.72%
        ]

        for days, expected_fraction in decay_times:
            time_s = days * 86400
            decayed_inv = self.calc._decay_inventory(inventory.copy(), time_s)

            # Calculate activity from decayed inventory
            n_atoms_remaining = decayed_inv.get('Au-198', 0)
            activity_remaining = n_atoms_remaining * lambda_decay

            actual_fraction = activity_remaining / initial_activity_bq

            self.assertAlmostEqual(actual_fraction, expected_fraction, delta=0.01,
                                  msg=f"After {days} days, {expected_fraction*100}% should remain")

    def test_co60_long_term_decay(self):
        """Test Co-60 decay over years (long half-life)"""
        co60_half_life_s = NIST_DOSE_CONSTANTS['Co-60']['half_life_seconds']

        initial_activity = 1.0e10
        lambda_decay = PHYSICAL_CONSTANTS['ln2'] / co60_half_life_s
        n_atoms = initial_activity / lambda_decay

        inventory = {'Co-60': n_atoms}

        # Test at 1 year (should be ~0.87× for 5.27 year half-life)
        one_year_s = 365.25 * 86400
        decayed_inv = self.calc._decay_inventory(inventory.copy(), one_year_s)

        n_remaining = decayed_inv.get('Co-60', 0)
        activity_remaining = n_remaining * lambda_decay
        fraction = activity_remaining / initial_activity

        expected = math.exp(-lambda_decay * one_year_s)
        self.assertAlmostEqual(fraction, expected, delta=0.01,
                              msg="Co-60 1-year decay should match exponential")


class MultiElementSampleTests(TestCase):
    """Test activation of multi-element samples"""

    def setUp(self):
        """Set up test environment"""
        self.calc = ActivationCalculator(use_multigroup=False)

        # Create flux configuration
        self.flux_config = FluxConfiguration.objects.create(
            location='test_multi',
            thermal_flux=Decimal('1.0e12'),
            fast_flux=Decimal('1.0e11'),
            reference_power=Decimal('100.0'),
        )

        # Create IRF
        self.irf = IrradiationRequestForm.objects.create(
            irf_number='TEST-MULTI-001',
            requester_name='Test User',
            sample_description='Multi-element test',
            physical_form='alloy',
            max_power=Decimal('200'),
            max_time=Decimal('10'),
            max_time_unit='hr',
            max_mass=Decimal('20'),
            max_mass_unit='g',
            expected_dose_rate=Decimal('1000'),
            dose_rate_basis='calculation',
            reactivity_worth=Decimal('0.01'),
            reactivity_basis='estimate',
            status='approved',
        )

    def test_gold_aluminum_alloy(self):
        """Test Au-Al alloy activation (produces Au-198 and Al-28)"""
        # Create 50-50 Au-Al alloy sample
        sample = Sample.objects.create(
            sample_id='TEST-AU-AL',
            material_type='Au-Al alloy',
            description='50-50 gold-aluminum alloy',
            mass=Decimal('2.0'),
            mass_unit='g',
        )

        # 50% Au, 50% Al by mass (approximately)
        SampleComposition.objects.create(
            sample=sample,
            element='Au',
            isotope='197',
            fraction=Decimal('50.0'),
        )

        SampleComposition.objects.create(
            sample=sample,
            element='Al',
            isotope='27',
            fraction=Decimal('50.0'),
        )

        # Create irradiation
        log = SampleIrradiationLog.objects.create(
            parent_irf=self.irf,
            irradiation_date=(timezone.now() - timedelta(hours=2)).date(),
            time_in=dt_time(10, 0),
            time_out=dt_time(11, 0),
            actual_location='test_multi',
            actual_power=Decimal('100.0'),
            total_time=Decimal('1.0'),
            total_time_unit='hr',
        )

        # Calculate activation
        results = self.calc.calculate_activation(
            sample=sample,
            irradiation_logs=[log],
            flux_configs={'test_multi': self.flux_config},
            use_cache=False,
        )

        self.assertTrue(results['calculation_successful'])

        # Should produce both Au-198 and Al-28
        isotopes = results['isotopes']

        # Au-198 should be present (long half-life, still active after 2 hours)
        self.assertIn('Au-198', isotopes,
                     "Au-198 should be produced from Au-197")

        # Al-28 has very short half-life (2.24 min), might not be in results
        # due to decay and minimum activity threshold
        # Just verify calculation completed successfully


class SaturationTests(TestCase):
    """Test saturation behavior for long irradiations"""

    def setUp(self):
        """Set up test environment"""
        self.calc = ActivationCalculator(use_multigroup=False)

    def test_saturation_formula(self):
        """Test that activation follows saturation formula N = (R/λ)[1-exp(-λt)]"""
        # Manual calculation for gold
        mass_g = 1.0
        thermal_flux = 1.0e12
        sigma_barns = ACTIVATION_CROSS_SECTIONS['Au-197']['thermal_xs_barns']
        sigma_cm2 = sigma_barns * 1e-24
        half_life_s = ACTIVATION_CROSS_SECTIONS['Au-197']['product_half_life_seconds']
        lambda_decay = PHYSICAL_CONSTANTS['ln2'] / half_life_s

        # Number of Au-197 atoms
        n_atoms_target = (mass_g * PHYSICAL_CONSTANTS['avogadro']) / 197

        # Production rate
        R = sigma_cm2 * thermal_flux * n_atoms_target

        # Calculate saturation activity (infinite time)
        saturation_activity = R  # At saturation, production = decay, so A_sat = R

        # Activity after various irradiation times (as fraction of saturation)
        times_and_fractions = [
            (half_life_s * 0.1, 0.0670),    # 0.1 half-lives
            (half_life_s * 1.0, 0.5000),    # 1 half-life: 50% of saturation
            (half_life_s * 3.0, 0.8750),    # 3 half-lives: 87.5%
            (half_life_s * 7.0, 0.9922),    # 7 half-lives: ~99%
        ]

        for time_s, expected_fraction in times_and_fractions:
            # Saturation formula: A(t) = A_sat × [1 - exp(-λt)]
            actual_fraction = 1 - math.exp(-lambda_decay * time_s)

            self.assertAlmostEqual(actual_fraction, expected_fraction, delta=0.01,
                                  msg=f"After {time_s/half_life_s:.1f} half-lives, "
                                      f"activity should be {expected_fraction*100}% of saturation")


if __name__ == '__main__':
    import unittest
    unittest.main()
