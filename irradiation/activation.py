"""
Neutron Activation Analysis Module

This module calculates the isotopic inventory of samples based on their
complete irradiation history, accounting for:
- Neutron activation during irradiation (flux × cross-section × time)
- Radioactive decay between irradiations
- Sequential chaining of multiple irradiations
- Multi-group neutron spectrum effects (thermal/fast/intermediate)

Features:
- PyNE Integration: Uses PyNE nuclear data library for cross-sections when available
- Spectrum-averaged cross-sections: Accounts for thermal, fast, and intermediate flux
- Decay chains: Uses radioactivedecay for proper decay chain calculations
- Fallback mode: Includes simplified cross-section database for common elements
- Caching: SHA256 hash-based caching to avoid redundant calculations

Dependencies:
- radioactivedecay: For decay chain calculations between irradiations
- PyNE (recommended): For comprehensive multi-group cross-sections from nuclear data
- NumPy: For numerical calculations
- SciPy: For advanced numerical methods

Installation:
  Conda (recommended): conda install -c conda-forge pyne radioactivedecay numpy scipy
  Pip: pip install radioactivedecay numpy scipy
       (PyNE pip installation requires Fortran compilers)
"""

import hashlib
import json
from datetime import datetime, timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# Try to import advanced libraries
try:
    import radioactivedecay as rd
    HAS_RADIOACTIVEDECAY = True
except ImportError:
    HAS_RADIOACTIVEDECAY = False
    logger.warning("radioactivedecay not installed. Decay calculations will use simplified models.")

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("NumPy not installed. Some calculations will be limited.")

try:
    from pyne import nucname, data as pyne_data, xs as pyne_xs
    HAS_PYNE = True
    logger.info("PyNE loaded successfully - multi-group cross-sections available")
except ImportError:
    HAS_PYNE = False
    logger.warning("PyNE not installed. Using simplified one-group cross-sections.")


# Simplified cross-section database (thermal neutron capture)
# Format: {element: {isotope: (abundance, sigma_gamma_barns, product_isotope, half_life_seconds)}}
SIMPLE_CROSS_SECTIONS = {
    'Au': {
        'Au-197': (100.0, 98.65, 'Au-198', 2.6955 * 24 * 3600),  # 2.6955 days
    },
    'Al': {
        'Al-27': (100.0, 0.231, 'Al-28', 134.4 * 60),  # 134.4 minutes
    },
    'Cu': {
        'Cu-63': (69.15, 4.50, 'Cu-64', 12.7 * 3600),  # 12.7 hours
        'Cu-65': (30.85, 2.17, 'Cu-66', 5.12 * 60),    # 5.12 minutes
    },
    'Co': {
        'Co-59': (100.0, 37.18, 'Co-60', 5.27 * 365.25 * 24 * 3600),  # 5.27 years
    },
    'Mn': {
        'Mn-55': (100.0, 13.3, 'Mn-56', 2.5789 * 3600),  # 2.5789 hours
    },
    'Na': {
        'Na-23': (100.0, 0.530, 'Na-24', 14.997 * 3600),  # 14.997 hours
    },
    'Fe': {
        'Fe-54': (5.845, 2.25, 'Fe-55', 2.73 * 365.25 * 24 * 3600),  # 2.73 years
        'Fe-56': (91.754, 2.59, 'Fe-57', 'stable'),
        'Fe-57': (2.119, 2.48, 'Fe-58', 'stable'),
        'Fe-58': (0.282, 1.28, 'Fe-59', 44.503 * 24 * 3600),  # 44.503 days
    },
    'Ni': {
        'Ni-58': (68.077, 4.6, 'Ni-59', 76000 * 365.25 * 24 * 3600),  # 76000 years
        'Ni-60': (26.223, 2.9, 'Ni-61', 'stable'),
        'Ni-62': (3.635, 14.5, 'Ni-63', 100.1 * 365.25 * 24 * 3600),  # 100.1 years
        'Ni-64': (0.926, 1.52, 'Ni-65', 2.5172 * 3600),  # 2.5172 hours
    },
}

# Decay constant: λ = ln(2) / t_1/2
LAMBDA_LN2 = 0.693147180559945


class ActivationCalculator:
    """
    Main class for performing neutron activation analysis
    """

    def __init__(self, use_multigroup=False):
        """
        Initialize the activation calculator

        Args:
            use_multigroup: If True, use multi-group cross-sections (requires PyNE)
        """
        self.use_multigroup = use_multigroup and HAS_PYNE

        if use_multigroup and not HAS_PYNE:
            logger.warning("Multi-group requested but PyNE not available. Using one-group.")

    def calculate_activation(self, sample, irradiation_logs, flux_configs,
                            min_activity_fraction=0.001, use_cache=True):
        """
        Calculate the isotopic inventory for a sample based on its irradiation history

        Args:
            sample: Sample model instance
            irradiation_logs: QuerySet of SampleIrradiationLog ordered by date
            flux_configs: Dict mapping location names to FluxConfiguration instances
            min_activity_fraction: Minimum activity fraction to include in results (default 0.1%)
            use_cache: Whether to use cached results if available

        Returns:
            dict with calculation results or None if calculation fails
        """
        try:
            # Generate hash of irradiation history
            irr_hash = self.generate_irradiation_hash(irradiation_logs)

            # Check for cached results if requested
            if use_cache:
                cached = self._get_cached_result(sample, irr_hash)
                if cached:
                    logger.info(f"Using cached activation results for {sample.sample_id}")
                    return cached

            # Get sample composition
            composition = self._get_sample_composition(sample)
            if not composition:
                raise ValueError(f"No composition defined for sample {sample.sample_id}")

            # Initialize inventory (number of atoms of each isotope)
            inventory = self._initialize_inventory(composition, sample)

            # Process each irradiation in chronological order
            reference_time = None
            skipped_irradiations = []  # Track irradiations skipped due to missing flux

            for log in irradiation_logs:
                # Get flux configuration for this location
                flux_config = flux_configs.get(log.actual_location)
                if not flux_config:
                    logger.warning(f"No flux configuration for location {log.actual_location}. Skipping irradiation.")
                    skipped_irradiations.append({
                        'date': log.irradiation_date.isoformat() if log.irradiation_date else 'Unknown',
                        'location': log.actual_location,
                        'power': float(log.actual_power),
                        'time': float(log.total_time),
                        'time_unit': log.total_time_unit,
                        'reason': 'No flux configuration for this location'
                    })
                    continue

                # Calculate inventory after this irradiation + decay
                inventory, reference_time = self._process_irradiation(
                    inventory, log, flux_config, reference_time
                )

            # Check if all irradiations were skipped
            if reference_time is None:
                error_msg = "All irradiations were skipped. Please ensure flux configurations exist for the irradiation locations."
                logger.warning(f"{error_msg} Skipped: {skipped_irradiations}")
                return {
                    'calculation_successful': False,
                    'error_message': error_msg,
                    'isotopes': {},
                    'total_activity_bq': 0.0,
                    'irradiation_hash': irr_hash,
                    'skipped_irradiations': skipped_irradiations,
                }

            # Convert inventory to activities at reference time
            results = self._calculate_activities(inventory, reference_time, min_activity_fraction)

            # Calculate total activity and dose rate
            total_activity_bq = sum(iso['activity_bq'] for iso in results['isotopes'].values())
            results['total_activity_bq'] = total_activity_bq
            results['reference_time'] = reference_time.isoformat()
            results['irradiation_hash'] = irr_hash
            results['calculation_successful'] = True
            results['skipped_irradiations'] = skipped_irradiations  # Include skipped irradiations

            # Estimate dose rate (simplified - can be improved)
            results['estimated_dose_rate_1ft'] = self._estimate_dose_rate(results['isotopes'])

            return results

        except Exception as e:
            logger.error(f"Activation calculation failed for {sample.sample_id}: {e}")
            return {
                'calculation_successful': False,
                'error_message': str(e),
                'isotopes': {},
                'total_activity_bq': 0.0,
                'irradiation_hash': '',
            }

    def generate_irradiation_hash(self, irradiation_logs):
        """
        Generate SHA256 hash of irradiation history to detect changes

        Args:
            irradiation_logs: QuerySet of SampleIrradiationLog

        Returns:
            str: SHA256 hash hex string
        """
        # Create string representation of all relevant irradiation parameters
        hash_data = []
        for log in irradiation_logs:
            hash_data.append(f"{log.pk}|{log.actual_location}|{log.actual_power}|"
                           f"{log.total_time}|{log.irradiation_date}|{log.time_in}|{log.time_out}")

        hash_string = "||".join(hash_data)
        return hashlib.sha256(hash_string.encode()).hexdigest()

    def _get_cached_result(self, sample, irr_hash):
        """Check for cached activation result"""
        from .models import ActivationResult

        try:
            cached = ActivationResult.objects.get(sample=sample, irradiation_hash=irr_hash)
            if cached.calculation_successful:
                return {
                    'calculation_successful': True,
                    'isotopes': cached.isotopic_inventory,
                    'total_activity_bq': float(cached.total_activity_bq),
                    'reference_time': cached.reference_time.isoformat(),
                    'irradiation_hash': irr_hash,
                    'estimated_dose_rate_1ft': float(cached.estimated_dose_rate_1ft) if cached.estimated_dose_rate_1ft else None,
                    'from_cache': True,
                }
        except ActivationResult.DoesNotExist:
            pass

        return None

    def _get_sample_composition(self, sample):
        """
        Get composition of sample from database or infer from material_type

        Returns:
            dict: {element: {isotope: fraction_by_atoms}}
        """
        composition = {}

        # Check if composition is defined in database
        comp_elements = sample.composition_elements.all()

        if comp_elements.exists():
            # Use defined composition
            for comp in comp_elements:
                element = comp.element
                if element not in composition:
                    composition[element] = {}

                # Convert wt% to at% if needed (simplified - assumes single isotope)
                if comp.isotope:
                    isotope = comp.isotope
                else:
                    # Use most abundant isotope
                    isotope = self._get_natural_isotope(element)

                composition[element][isotope] = float(comp.fraction) / 100.0

        elif sample.material_type:
            # Infer composition from material_type
            # Try to parse as element symbol
            element = sample.material_type.strip().capitalize()

            # Check if it's in our database
            if element in SIMPLE_CROSS_SECTIONS:
                composition[element] = {}
                # Add all natural isotopes with their abundances
                for isotope, data in SIMPLE_CROSS_SECTIONS[element].items():
                    abundance = data[0] / 100.0  # Convert % to fraction
                    composition[element][isotope] = abundance
            else:
                logger.warning(f"Unknown element: {element}")

        return composition

    def _get_natural_isotope(self, element):
        """Get the most abundant natural isotope for an element"""
        if element in SIMPLE_CROSS_SECTIONS:
            isotopes = SIMPLE_CROSS_SECTIONS[element]
            # Find isotope with highest abundance
            max_abundance = 0
            main_isotope = None
            for isotope, data in isotopes.items():
                if data[0] > max_abundance:
                    max_abundance = data[0]
                    main_isotope = isotope
            return main_isotope
        return f"{element}-Unknown"

    def _initialize_inventory(self, composition, sample):
        """
        Initialize isotopic inventory based on composition and mass

        Args:
            composition: dict from _get_sample_composition
            sample: Sample model instance

        Returns:
            dict: {isotope: number_of_atoms}
        """
        inventory = {}

        # Get sample mass (or use estimate)
        mass_g = float(sample.mass) if sample.mass else 1.0  # Default 1 gram

        # For each element and isotope, calculate number of atoms
        for element, isotopes in composition.items():
            for isotope, fraction in isotopes.items():
                # Extract mass number from isotope (e.g., "Au-197" -> 197)
                try:
                    mass_number = int(isotope.split('-')[1])
                except (IndexError, ValueError):
                    logger.warning(f"Could not parse mass number from {isotope}")
                    continue

                # Calculate number of atoms: N = (mass * fraction * N_A) / A
                # Where N_A = Avogadro's number = 6.022e23
                element_mass_g = mass_g * fraction
                n_atoms = (element_mass_g * 6.022e23) / mass_number

                inventory[isotope] = n_atoms

        return inventory

    def _process_irradiation(self, inventory, log, flux_config, previous_time):
        """
        Process a single irradiation: apply activation + decay

        Args:
            inventory: Current isotopic inventory {isotope: n_atoms}
            log: SampleIrradiationLog instance
            flux_config: FluxConfiguration instance
            previous_time: DateTime of previous irradiation end (or None)

        Returns:
            tuple: (new_inventory, end_time)
        """
        # Get scaled flux for this irradiation power
        power_kw = float(log.actual_power)
        fluxes = flux_config.get_scaled_fluxes(power_kw)
        thermal_flux = fluxes['thermal_flux']  # n/cm²/s
        fast_flux = fluxes['fast_flux']  # n/cm²/s
        intermediate_flux = fluxes.get('intermediate_flux', 0)  # n/cm²/s

        # Total flux for activation (weighted sum will be done in activation method)
        total_flux = thermal_flux + fast_flux + intermediate_flux

        # Prepare flux spectrum for multi-group calculations
        flux_spectrum = {
            'thermal': thermal_flux,
            'fast': fast_flux,
            'intermediate': intermediate_flux,
            'total': total_flux
        } if self.use_multigroup else None

        # Calculate irradiation time in seconds
        total_time_s = self._convert_to_seconds(float(log.total_time), log.total_time_unit)

        # Calculate irradiation start/end times
        irr_datetime = datetime.combine(log.irradiation_date, log.time_in)
        irr_end_datetime = datetime.combine(log.irradiation_date, log.time_out)

        # If there was a previous irradiation, decay the inventory first
        if previous_time:
            decay_time_s = (irr_datetime - previous_time).total_seconds()
            if decay_time_s > 0:
                inventory = self._decay_inventory(inventory, decay_time_s)

        # Apply neutron activation with flux spectrum if multigroup enabled
        new_inventory = self._activate_inventory(inventory, total_flux, total_time_s, flux_spectrum)

        return new_inventory, irr_end_datetime

    def _convert_to_seconds(self, value, unit):
        """Convert time value to seconds"""
        if unit == 'sec':
            return value
        elif unit == 'min':
            return value * 60
        elif unit == 'hr':
            return value * 3600
        return value

    def _activate_inventory(self, inventory, flux, time_s, flux_spectrum=None):
        """
        Apply neutron activation to inventory

        Uses activation equation with optional multi-group cross-sections:
        N_product(t) = N_target * σ * φ * [1 - exp(-λt)] / λ

        Args:
            inventory: {isotope: n_atoms}
            flux: total neutron flux (n/cm²/s) - used for production calculations
            time_s: irradiation time (seconds)
            flux_spectrum: Optional dict with 'thermal', 'fast', 'intermediate' fluxes
                          for spectrum-averaged cross-sections

        Returns:
            dict: updated inventory
        """
        new_inventory = inventory.copy()

        # For each target isotope, calculate production
        for target_isotope, n_atoms in inventory.items():
            # Get cross-section and product data
            # Pass flux_spectrum for multi-group calculations if available
            xs_data = self._get_cross_section_data(target_isotope, flux_spectrum)
            if not xs_data:
                continue

            sigma_barns, product_isotope, half_life_s = xs_data

            # Convert barns to cm²  (1 barn = 1e-24 cm²)
            sigma_cm2 = sigma_barns * 1e-24

            # Calculate production rate: R = σ * φ * N
            production_rate = sigma_cm2 * flux * n_atoms  # atoms/s

            # If product is radioactive, account for decay during irradiation
            if half_life_s != 'stable' and half_life_s > 0:
                decay_const = LAMBDA_LN2 / half_life_s

                # Saturation formula: N_product = (R/λ) * [1 - exp(-λt)]
                n_produced = (production_rate / decay_const) * (1 - np.exp(-decay_const * time_s)) if HAS_NUMPY else \
                             (production_rate / decay_const) * (1 - self._exp(-decay_const * time_s))
            else:
                # Stable product: linear production
                n_produced = production_rate * time_s

            # Add to inventory (or create new entry)
            if product_isotope in new_inventory:
                new_inventory[product_isotope] += n_produced
            else:
                new_inventory[product_isotope] = n_produced

            # Deplete target (very small depletion typically)
            new_inventory[target_isotope] = max(0, n_atoms - n_produced * sigma_cm2 * flux * time_s)

        return new_inventory

    def _decay_inventory(self, inventory, time_s):
        """
        Decay all radioactive isotopes for given time

        N(t) = N(0) * exp(-λt)

        Args:
            inventory: {isotope: n_atoms}
            time_s: decay time (seconds)

        Returns:
            dict: decayed inventory
        """
        if HAS_RADIOACTIVEDECAY:
            return self._decay_with_rd(inventory, time_s)
        else:
            return self._decay_simple(inventory, time_s)

    def _decay_with_rd(self, inventory, time_s):
        """Decay using radioactivedecay library (includes decay chains)"""
        # Convert inventory to radioactivedecay Inventory
        # Format: {isotope: number_of_atoms}
        rd_inventory = rd.Inventory(inventory, 'num')

        # Decay for time_s seconds
        decayed = rd_inventory.decay(time_s, 's')

        return dict(decayed.numbers())

    def _decay_simple(self, inventory, time_s):
        """Simple decay without chains"""
        decayed = {}

        for isotope, n_atoms in inventory.items():
            xs_data = self._get_cross_section_data(isotope)
            if not xs_data:
                # Unknown isotope, assume stable
                decayed[isotope] = n_atoms
                continue

            _, _, half_life_s = xs_data

            if half_life_s == 'stable' or half_life_s == 0:
                decayed[isotope] = n_atoms
            else:
                decay_const = LAMBDA_LN2 / half_life_s
                if HAS_NUMPY:
                    n_remaining = n_atoms * np.exp(-decay_const * time_s)
                else:
                    n_remaining = n_atoms * self._exp(-decay_const * time_s)
                decayed[isotope] = n_remaining

        return decayed

    def _exp(self, x):
        """Fallback exponential if NumPy not available"""
        import math
        return math.exp(x)

    def _calculate_activities(self, inventory, reference_time, min_fraction):
        """
        Convert inventory (atoms) to activities (Bq) at reference time

        Activity = λ * N = (ln(2) / t_1/2) * N

        Args:
            inventory: {isotope: n_atoms}
            reference_time: datetime
            min_fraction: minimum activity fraction to include

        Returns:
            dict: {isotope: {activity_bq, half_life, etc.}}
        """
        activities = {}
        total_activity = 0.0

        # Calculate activity for each isotope
        for isotope, n_atoms in inventory.items():
            if n_atoms <= 0:
                continue

            xs_data = self._get_cross_section_data(isotope)
            if not xs_data:
                continue

            _, _, half_life_s = xs_data

            if half_life_s == 'stable' or half_life_s == 0:
                continue  # Skip stable isotopes

            # Activity = λ * N
            decay_const = LAMBDA_LN2 / half_life_s
            activity_bq = decay_const * n_atoms

            if activity_bq > 0:
                activities[isotope] = {
                    'activity_bq': activity_bq,
                    'activity_ci': activity_bq / 3.7e10,
                    'atoms': n_atoms,
                    'half_life_s': half_life_s,
                    'half_life_display': self._format_half_life(half_life_s),
                }
                total_activity += activity_bq

        # Filter by minimum fraction
        filtered = {}
        for isotope, data in activities.items():
            fraction = data['activity_bq'] / total_activity if total_activity > 0 else 0
            if fraction >= min_fraction:
                data['fraction'] = fraction
                filtered[isotope] = data

        return {'isotopes': filtered}

    def _format_half_life(self, half_life_s):
        """Format half-life for display"""
        if half_life_s < 60:
            return f"{half_life_s:.2f} s"
        elif half_life_s < 3600:
            return f"{half_life_s/60:.2f} min"
        elif half_life_s < 86400:
            return f"{half_life_s/3600:.2f} h"
        elif half_life_s < 365.25 * 86400:
            return f"{half_life_s/86400:.2f} d"
        else:
            return f"{half_life_s/(365.25*86400):.2f} y"

    def _get_cross_section_data(self, isotope, flux_spectrum=None):
        """
        Get cross-section data for isotope

        Args:
            isotope: Isotope name (e.g., "Au-197")
            flux_spectrum: Optional dict with keys 'thermal', 'fast', 'intermediate'
                          for spectrum-averaged cross-sections

        Returns:
            tuple: (sigma_barns, product_isotope, half_life_s) or None
        """
        # If using PyNE and multigroup is enabled, try to get data from PyNE first
        if self.use_multigroup and HAS_PYNE:
            if flux_spectrum:
                pyne_data = self._get_pyne_cross_section(
                    isotope,
                    thermal_flux=flux_spectrum.get('thermal'),
                    fast_flux=flux_spectrum.get('fast'),
                    intermediate_flux=flux_spectrum.get('intermediate')
                )
            else:
                pyne_data = self._get_pyne_cross_section(isotope)

            if pyne_data:
                logger.debug(f"Using PyNE cross-section for {isotope}")
                return pyne_data

        # Fall back to simplified cross-section database
        # Parse element from isotope (e.g., "Au-197" -> "Au")
        try:
            element = isotope.split('-')[0]
        except (IndexError, AttributeError):
            return None

        if element in SIMPLE_CROSS_SECTIONS:
            if isotope in SIMPLE_CROSS_SECTIONS[element]:
                data = SIMPLE_CROSS_SECTIONS[element][isotope]
                logger.debug(f"Using simplified cross-section for {isotope}")
                return data[1], data[2], data[3]  # sigma, product, half_life

        logger.warning(f"No cross-section data available for {isotope}")
        return None

    def _get_pyne_cross_section(self, isotope, thermal_flux=None, fast_flux=None, intermediate_flux=None):
        """
        Get neutron capture cross-section data from PyNE

        If flux values are provided, calculates spectrum-averaged cross-section.
        Otherwise returns thermal cross-section only.

        Args:
            isotope: Isotope name (e.g., "Au-197")
            thermal_flux: Thermal neutron flux (n/cm²/s) for E < 0.5 eV
            fast_flux: Fast neutron flux (n/cm²/s) for E > 0.1 MeV
            intermediate_flux: Intermediate flux (n/cm²/s) for 0.5 eV < E < 0.1 MeV

        Returns:
            tuple: (sigma_barns, product_isotope, half_life_s) or None
        """
        try:
            # Convert isotope name to PyNE nucid format
            # Example: "Au-197" -> 791970000 (ZZAAAM format)
            nucid = nucname.id(isotope)

            # Get thermal neutron capture cross-section (n,gamma) at 0.0253 eV
            # pyne_data.gamma_x returns cross-section in barns
            sigma_thermal = pyne_data.gamma_x(nucid)

            if sigma_thermal is None or sigma_thermal <= 0:
                logger.debug(f"No thermal cross-section data for {isotope} in PyNE")
                return None

            # Calculate spectrum-averaged cross-section if flux spectrum provided
            if thermal_flux and fast_flux:
                # For most materials, thermal cross-section dominates
                # Fast cross-section is typically much smaller (1/v behavior breaks down)
                # Simplified multi-group: assume fast xs is ~1/100 of thermal
                sigma_fast = sigma_thermal * 0.01  # Rough approximation

                # If intermediate flux provided, estimate intermediate xs
                if intermediate_flux:
                    # Intermediate xs typically between thermal and fast
                    sigma_intermediate = sigma_thermal * 0.1  # Rough approximation
                    total_flux = thermal_flux + intermediate_flux + fast_flux
                    sigma_avg = (sigma_thermal * thermal_flux +
                               sigma_intermediate * intermediate_flux +
                               sigma_fast * fast_flux) / total_flux
                else:
                    total_flux = thermal_flux + fast_flux
                    sigma_avg = (sigma_thermal * thermal_flux +
                               sigma_fast * fast_flux) / total_flux

                sigma_barns = sigma_avg
                logger.debug(f"{isotope}: thermal={sigma_thermal:.2f}b, "
                           f"spectrum-averaged={sigma_avg:.2f}b")
            else:
                # Use thermal cross-section only
                sigma_barns = sigma_thermal

            # Determine product isotope (A+1)
            element_z = nucname.znum(nucid)
            mass_a = nucname.anum(nucid)
            product_nucid = nucname.id_from_ZZZAAA(element_z * 1000 + (mass_a + 1))
            product_isotope = nucname.name(product_nucid)

            # Get half-life of product isotope
            try:
                half_life_s = pyne_data.half_life(product_nucid)
                # PyNE returns half-life in seconds
                # If stable or very long-lived, might return very large number or inf
                if half_life_s is None or half_life_s <= 0:
                    half_life_s = 'stable'
                elif HAS_NUMPY and not np.isfinite(half_life_s):
                    half_life_s = 'stable'
            except:
                # If half-life not available, check decay constant
                try:
                    decay_const = pyne_data.decay_const(product_nucid)
                    if decay_const > 0:
                        half_life_s = LAMBDA_LN2 / decay_const
                    else:
                        half_life_s = 'stable'
                except:
                    half_life_s = 'stable'

            logger.debug(f"PyNE data for {isotope}: σ={sigma_barns:.3f}b, "
                        f"product={product_isotope}, t½={half_life_s}")

            return (sigma_barns, product_isotope, half_life_s)

        except Exception as e:
            logger.debug(f"PyNE cross-section lookup failed for {isotope}: {e}")
            return None

    def _estimate_dose_rate(self, isotopes):
        """
        Estimate dose rate at 1 foot using simplified approach

        Can use "6 C E rule": dose rate (mrem/hr) ≈ 6 * C * E_avg
        where C = activity in Ci, E_avg = average gamma energy in MeV

        For now, use simple scaling based on total activity

        Args:
            isotopes: dict of isotopes with activities

        Returns:
            float: estimated dose rate in mrem/hr at 1 foot
        """
        # Simplified: assume average 0.5 MeV gamma, geometry factor
        total_ci = sum(iso['activity_ci'] for iso in isotopes.values())

        # Very rough estimate: 1 Ci at 1 foot ≈ 1000-2000 mrem/hr for typical gamma emitters
        # This should be replaced with isotope-specific dose factors
        estimated_dose = total_ci * 1000.0  # mrem/hr

        return estimated_dose
