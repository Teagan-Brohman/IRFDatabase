"""
Neutron Activation Analysis Module

This module calculates the isotopic inventory of samples based on their
complete irradiation history, accounting for:
- Neutron activation during irradiation (flux × cross-section × time)
- Radioactive decay between irradiations
- Sequential chaining of multiple irradiations
- Multi-group neutron spectrum effects (thermal/fast/intermediate)

Features:
- PyNE Integration: Uses PyNE DataSource interface for energy-dependent cross-sections
- Multi-group Cross Sections: Proper energy-group structures (thermal, epithermal, fast)
- Spectrum Collapse: Flux-weighted averaging of multi-group cross sections to one-group
- Multiple Data Sources: SimpleDataSource, EAFDataSource, and ENDF readers
- Decay chains: Uses radioactivedecay for proper decay chain calculations
- Fallback mode: Includes simplified cross-section database for common elements
- Caching: SHA256 hash-based caching to avoid redundant calculations

Cross Section Methodology:
- Energy Groups:
  * Thermal: E < 0.5 eV (Maxwell-Boltzmann spectrum at reactor temperature)
  * Intermediate/Epithermal: 0.5 eV < E < 0.1 MeV (1/E slowing down spectrum)
  * Fast: 0.1 MeV < E < 10 MeV (fission spectrum)
- Spectrum Collapse: σ_eff = Σ(σ_g × φ_g) / Σ(φ_g) where g = energy group
- Data Priority: SimpleDataSource → EAFDataSource → Fallback database

Dependencies:
- radioactivedecay: For decay chain calculations between irradiations
- PyNE (recommended): For comprehensive multi-group cross-sections from nuclear data
- NumPy: For numerical calculations and multi-group arrays
- SciPy: For advanced numerical methods

Installation:
  Conda (recommended): conda install -c conda-forge pyne radioactivedecay numpy scipy
  Pip: pip install radioactivedecay numpy scipy
       (PyNE pip installation requires Fortran compilers)

ENDF Data (Optional):
  For the most accurate cross sections, PyNE can use ENDF/B-VIII.0 data.
  The built-in data sources (Simple, EAF) provide good accuracy for most applications.
  To add ENDF data:
    1. Download ENDF/B-VIII.0 from https://www.nndc.bnl.gov/endf/
    2. Use PyNE's ENDF reader: from pyne.endf import Library
    3. Process with NJOY or use PyNE's OpenMC data source
  See: https://pyne.io/examples/endf_reader.html
"""

import hashlib
import json
from datetime import datetime, timedelta
from django.utils import timezone
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
                            min_activity_fraction=0.001, use_cache=True, track_timeline=True):
        """
        Calculate the isotopic inventory for a sample based on its irradiation history

        Args:
            sample: Sample model instance
            irradiation_logs: QuerySet of SampleIrradiationLog ordered by date
            flux_configs: Dict mapping location names to FluxConfiguration instances
            min_activity_fraction: Minimum activity fraction to include in results (default 0.1%)
            use_cache: Whether to use cached results if available
            track_timeline: If True, save intermediate states to timeline (default: True)

        Returns:
            dict with calculation results or None if calculation fails
        """
        try:
            # Generate hash of irradiation history AND sample composition
            irr_hash = self.generate_irradiation_hash(irradiation_logs, sample=sample)

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

            # Initialize timeline tracking
            timeline = [] if track_timeline else None
            step_number = 0

            # Save initial state if tracking timeline
            if track_timeline and len(irradiation_logs) > 0:
                first_irr_date = timezone.make_aware(datetime.combine(
                    irradiation_logs[0].irradiation_date,
                    irradiation_logs[0].time_in
                )) - timedelta(days=1)

                timeline.append({
                    'step_number': step_number,
                    'step_type': 'initial',
                    'step_datetime': first_irr_date,
                    'description': 'Initial state (before irradiation)',
                    'inventory': inventory.copy(),
                    'irradiation_log': None,
                    'decay_time_seconds': None
                })
                step_number += 1

            # Process each irradiation in chronological order
            reference_time = None
            skipped_irradiations = []  # Track irradiations skipped due to missing flux

            for log in irradiation_logs:
                # Get flux configuration for this location
                # Try exact match first, then try case-insensitive match
                flux_config = flux_configs.get(log.actual_location)

                # If exact match fails, try case-insensitive matching
                if not flux_config:
                    location_lower = log.actual_location.lower()
                    for config_location, config in flux_configs.items():
                        if config_location.lower() == location_lower:
                            flux_config = config
                            logger.info(f"Matched '{log.actual_location}' to '{config_location}' (case-insensitive)")
                            break

                if not flux_config:
                    available_locations = list(flux_configs.keys())
                    logger.warning(
                        f"No flux configuration for location '{log.actual_location}'. "
                        f"Available locations: {available_locations}. Skipping irradiation."
                    )
                    skipped_irradiations.append({
                        'date': log.irradiation_date.isoformat() if log.irradiation_date else 'Unknown',
                        'location': log.actual_location,
                        'power': float(log.actual_power),
                        'time': float(log.total_time),
                        'time_unit': log.total_time_unit,
                        'reason': f'No flux configuration for location "{log.actual_location}". Available: {", ".join(available_locations)}'
                    })
                    continue

                # Track decay period if there was a previous irradiation
                if track_timeline and reference_time:
                    irr_start = timezone.make_aware(datetime.combine(log.irradiation_date, log.time_in))
                    decay_time_s = (irr_start - reference_time).total_seconds()

                    if decay_time_s > 0:
                        # Decay inventory for timeline (actual decay happens in _process_irradiation)
                        decayed_inventory = self._decay_inventory(inventory.copy(), decay_time_s)

                        timeline.append({
                            'step_number': step_number,
                            'step_type': 'decay',
                            'step_datetime': irr_start - timedelta(seconds=1),
                            'description': f'After {decay_time_s/86400:.1f} day decay period',
                            'inventory': decayed_inventory,
                            'irradiation_log': None,
                            'decay_time_seconds': int(decay_time_s)
                        })
                        step_number += 1

                # Calculate inventory after this irradiation + decay
                inventory, reference_time = self._process_irradiation(
                    inventory, log, flux_config, reference_time
                )

                # Track post-irradiation state
                if track_timeline:
                    timeline.append({
                        'step_number': step_number,
                        'step_type': 'irradiation',
                        'step_datetime': reference_time,
                        'description': f'After irradiation at {log.actual_location}',
                        'inventory': inventory.copy(),
                        'irradiation_log': log,
                        'decay_time_seconds': None
                    })
                    step_number += 1

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

            # Decay to current date if tracking timeline
            if track_timeline and reference_time:
                current_date = timezone.now()
                if current_date > reference_time:
                    decay_to_current_s = (current_date - reference_time).total_seconds()

                    # Decay inventory to current date
                    current_inventory = self._decay_inventory(inventory.copy(), decay_to_current_s)

                    # Save current state to timeline
                    timeline.append({
                        'step_number': step_number,
                        'step_type': 'current',
                        'step_datetime': current_date,
                        'description': f'Current date ({decay_to_current_s/86400:.0f} days after last irradiation)',
                        'inventory': current_inventory,
                        'irradiation_log': None,
                        'decay_time_seconds': int(decay_to_current_s)
                    })

            # Decay inventory to current date for main results display
            current_date = timezone.now()
            end_of_irradiation_time = reference_time

            if current_date > reference_time:
                # Calculate decay time from end of last irradiation to now
                decay_to_current_s = (current_date - reference_time).total_seconds()

                # Decay inventory to current date
                current_inventory = self._decay_inventory(inventory.copy(), decay_to_current_s)

                # Calculate activities at current date
                results = self._calculate_activities(current_inventory, current_date, min_activity_fraction)

                # Store both reference times
                results['reference_time'] = current_date.isoformat()
                results['end_of_irradiation_time'] = end_of_irradiation_time.isoformat()
                results['decay_time_days'] = decay_to_current_s / 86400.0

                logger.info(f"Decayed {decay_to_current_s/86400:.1f} days from end of irradiation to current date")
            else:
                # Current date is before or at reference time (shouldn't happen, but handle gracefully)
                results = self._calculate_activities(inventory, reference_time, min_activity_fraction)
                results['reference_time'] = reference_time.isoformat()
                results['end_of_irradiation_time'] = end_of_irradiation_time.isoformat()
                results['decay_time_days'] = 0.0

            # Calculate total activity and dose rate at current date
            total_activity_bq = results.get('total_activity_bq', 0.0)
            results['total_activity_bq'] = total_activity_bq
            results['irradiation_hash'] = irr_hash
            results['calculation_successful'] = True
            results['skipped_irradiations'] = skipped_irradiations  # Include skipped irradiations
            results['timeline'] = timeline if track_timeline else None  # Include timeline

            # Estimate dose rate using isotope-specific gamma energies
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

    def generate_irradiation_hash(self, irradiation_logs, sample=None):
        """
        Generate SHA256 hash of irradiation history AND sample composition to detect changes

        Args:
            irradiation_logs: QuerySet of SampleIrradiationLog
            sample: Sample instance (optional, to include composition in hash)

        Returns:
            str: SHA256 hash hex string
        """
        # Create string representation of all relevant irradiation parameters
        hash_data = []

        # Version number - increment when calculation logic changes to invalidate cache
        # v3: Fixed PyNE gamma energy lookup to handle list-of-tuples format
        hash_data.append("VERSION:3")

        # Include sample composition if provided
        if sample:
            composition = self._get_sample_composition(sample)
            comp_strings = []
            for element, data in sorted(composition.items()):
                if isinstance(data, dict):
                    # Isotopic composition
                    for isotope, fraction in sorted(data.items()):
                        comp_strings.append(f"{isotope}:{fraction}")
                else:
                    # Elemental composition
                    comp_strings.append(f"{element}:{data}")
            hash_data.append(f"COMPOSITION:{','.join(comp_strings)}")

            # Include sample mass
            if sample.mass:
                hash_data.append(f"MASS:{sample.mass}|{sample.mass_unit}")

        # Include irradiation parameters
        for log in irradiation_logs:
            hash_data.append(f"{log.pk}|{log.actual_location}|{log.actual_power}|"
                           f"{log.total_time}|{log.irradiation_date}|{log.time_in}|{log.time_out}")

        hash_string = "||".join(hash_data)
        return hashlib.sha256(hash_string.encode()).hexdigest()

    def _save_timeline_to_db(self, activation_result, timeline, min_activity_fraction=0.001):
        """
        Save timeline entries to database

        Args:
            activation_result: ActivationResult instance
            timeline: List of timeline dictionaries from calculate_activation
            min_activity_fraction: Minimum activity fraction for dominant isotopes

        Returns:
            Number of timeline entries created
        """
        from .models import ActivationTimeline
        from decimal import Decimal

        if not timeline:
            logger.debug("No timeline to save")
            return 0

        # Clear existing timeline for this result
        ActivationTimeline.objects.filter(activation_result=activation_result).delete()

        entries_created = 0

        # Create timeline entries
        for entry in timeline:
            # Calculate activities for this inventory
            activities = self._calculate_activities(
                entry['inventory'],
                entry['step_datetime'],
                min_activity_fraction
            )

            # Calculate total activity
            total_activity = activities.get('total_activity_bq', 0.0)

            # Get top 5 dominant isotopes
            dominant = {}
            sorted_isotopes = sorted(
                activities['isotopes'].items(),
                key=lambda x: x[1]['activity_bq'],
                reverse=True
            )[:5]

            for isotope, data in sorted_isotopes:
                dominant[isotope] = data['activity_bq']

            # Calculate dose rate
            dose_rate = self._estimate_dose_rate(activities['isotopes'])

            # Create timeline entry
            ActivationTimeline.objects.create(
                activation_result=activation_result,
                step_number=entry['step_number'],
                step_type=entry['step_type'],
                step_datetime=entry['step_datetime'],
                description=entry['description'],
                inventory=entry['inventory'],
                total_activity_bq=Decimal(str(total_activity)),
                dominant_isotopes=dominant,
                estimated_dose_rate_1ft=Decimal(str(dose_rate)) if dose_rate else None,
                irradiation_log=entry.get('irradiation_log'),
                decay_time_seconds=entry.get('decay_time_seconds')
            )
            entries_created += 1

        logger.info(f"Saved {entries_created} timeline entries for {activation_result}")
        return entries_created

    def decay_to_date(self, sample, target_date, irradiation_logs=None, flux_configs=None,
                     min_activity_fraction=0.001):
        """
        Calculate isotopic inventory and activity at an arbitrary future date

        This method calculates the complete activation history through all irradiations,
        then decays the final inventory to the specified target date.

        Args:
            sample: Sample instance
            target_date: datetime object for target date (must be timezone-aware or naive to match logs)
            irradiation_logs: Optional QuerySet of SampleIrradiationLog entries
                            (if None, fetches from database)
            flux_configs: Optional dict mapping location -> FluxConfiguration
                         (if None, fetches from database)
            min_activity_fraction: Minimum activity fraction to include in results (default 0.001)

        Returns:
            dict with:
                'success': bool - whether calculation succeeded
                'target_date': str - ISO format of target date
                'inventory': dict - isotopic inventory at target date {isotope: n_atoms}
                'activities': dict - activity data at target date
                'total_activity_bq': float - total activity in Bq
                'total_activity_mci': float - total activity in mCi
                'total_activity_ci': float - total activity in Ci
                'estimated_dose_rate_1ft': float - dose rate in mrem/hr at 1 foot
                'decay_time_seconds': int - seconds from last irradiation to target date
                'decay_time_days': float - days from last irradiation to target date
                'last_irradiation_date': str - ISO format of last irradiation
                'error': str - error message if success=False
        """
        from datetime import datetime

        # Get irradiation logs if not provided
        if irradiation_logs is None:
            irradiation_logs = sample.irradiation_logs.all().order_by('irradiation_datetime')

        # Check if there are any irradiations
        if not irradiation_logs.exists():
            return {
                'success': False,
                'error': 'Sample has no irradiation history',
                'target_date': target_date.isoformat(),
            }

        # Calculate activation through all irradiations (without timeline tracking to save processing)
        results = self.calculate_activation(
            sample=sample,
            irradiation_logs=irradiation_logs,
            flux_configs=flux_configs,
            min_activity_fraction=min_activity_fraction,
            use_cache=False,  # Don't use cache for intermediate calculation
            track_timeline=False  # Don't need full timeline, just final inventory
        )

        if not results.get('calculation_successful', False):
            return {
                'success': False,
                'error': results.get('error', 'Activation calculation failed'),
                'target_date': target_date.isoformat(),
            }

        # Get the reference time (end of last irradiation)
        last_log = irradiation_logs.last()
        last_irradiation_date = results.get('reference_time')

        if isinstance(last_irradiation_date, str):
            last_irradiation_date = datetime.fromisoformat(last_irradiation_date)

        # Validate target date is after last irradiation
        if target_date < last_irradiation_date:
            return {
                'success': False,
                'error': f'Target date ({target_date.isoformat()}) is before last irradiation ({last_irradiation_date.isoformat()})',
                'target_date': target_date.isoformat(),
                'last_irradiation_date': last_irradiation_date.isoformat(),
            }

        # Calculate decay time
        decay_time = target_date - last_irradiation_date
        decay_time_seconds = int(decay_time.total_seconds())
        decay_time_days = decay_time_seconds / 86400.0

        # Get final inventory from activation calculation
        # The inventory is stored in results['isotopes'] with activity data
        # We need to reconstruct atom counts from the activities
        final_inventory = {}
        isotopes_data = results.get('isotopes', {})

        # For each isotope in the results, get the number of atoms
        # This is tricky because results store activity, not atoms
        # We need to back-calculate: N = Activity / λ where λ = ln(2)/t_half
        for isotope, iso_data in isotopes_data.items():
            activity_bq = iso_data.get('activity_bq', 0)
            half_life_s = iso_data.get('half_life_s', iso_data.get('half_life_seconds', None))

            if half_life_s and half_life_s > 0 and activity_bq > 0:
                decay_constant = np.log(2) / half_life_s
                n_atoms = activity_bq / decay_constant
                final_inventory[isotope] = n_atoms
            elif activity_bq > 0:
                # Stable isotope or unknown half-life - store with zero activity
                final_inventory[isotope] = 0

        # Also include stable parent isotopes from composition
        composition = self._get_sample_composition(sample)
        for element, isotopes in composition.items():
            for isotope, fraction in isotopes.items():
                if isotope not in final_inventory:
                    # Calculate initial number of atoms
                    n_atoms = self._calculate_initial_atoms(sample, element, isotope, fraction)
                    final_inventory[isotope] = n_atoms

        # Decay inventory to target date
        decayed_inventory = self._decay_inventory(final_inventory.copy(), decay_time_seconds)

        # Calculate activities at target date
        activities = self._calculate_activities(
            decayed_inventory,
            target_date,
            min_activity_fraction
        )

        total_activity_bq = activities.get('total_activity_bq', 0.0)

        # Estimate dose rate
        dose_rate = self._estimate_dose_rate(activities['isotopes'])

        return {
            'success': True,
            'target_date': target_date.isoformat(),
            'last_irradiation_date': last_irradiation_date.isoformat(),
            'decay_time_seconds': decay_time_seconds,
            'decay_time_days': decay_time_days,
            'inventory': decayed_inventory,
            'activities': activities,
            'total_activity_bq': total_activity_bq,
            'total_activity_mci': total_activity_bq / 3.7e10 * 1000,  # Convert to mCi
            'total_activity_ci': total_activity_bq / 3.7e10,  # Convert to Ci
            'estimated_dose_rate_1ft': dose_rate,
            'number_of_isotopes': len(activities['isotopes']),
        }

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

    def _calculate_initial_atoms(self, sample, element, isotope, fraction):
        """
        Calculate initial number of atoms for a given element/isotope in sample

        Args:
            sample: Sample instance
            element: Element symbol (e.g., 'Au')
            isotope: Isotope name (e.g., 'Au-197')
            fraction: Atomic fraction (0-1)

        Returns:
            float: Number of atoms
        """
        # Get sample mass
        if not sample.mass:
            return 0

        mass_value = float(sample.mass)
        mass_unit = sample.mass_unit if sample.mass_unit else 'g'

        # Convert to grams
        if mass_unit == 'mg':
            mass_g = mass_value / 1000.0
        elif mass_unit == 'kg':
            mass_g = mass_value * 1000.0
        else:  # 'g' or default
            mass_g = mass_value

        # Extract mass number from isotope name (e.g., "Au-197" -> 197)
        try:
            mass_number = int(isotope.split('-')[1])
        except (IndexError, ValueError):
            # If can't parse, use natural isotope mass number
            logger.warning(f"Could not parse mass number from {isotope}, using approximate value")
            mass_number = 197  # Default for gold, adjust as needed

        # Calculate number of atoms: N = (mass * fraction * N_A) / A
        # Where N_A = Avogadro's number = 6.022e23
        element_mass_g = mass_g * fraction
        n_atoms = (element_mass_g * 6.022e23) / mass_number

        return n_atoms

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

                element_fraction = float(comp.fraction) / 100.0  # Element's fraction in sample

                # Convert wt% to at% if needed (simplified - assumes single isotope)
                if comp.isotope and comp.isotope.lower() not in ['natural', 'nat', '']:
                    # Specific isotope specified
                    # Format as "Element-Mass" (e.g., "Au-197")
                    # Remove element prefix if it's duplicated (e.g., "U-235" not "U-U-235")
                    isotope_part = comp.isotope.replace(f"{element}-", "").strip()
                    isotope = f"{element}-{isotope_part}"
                    composition[element][isotope] = element_fraction
                else:
                    # Natural abundance - get all isotopes
                    natural_isotopes = self._get_natural_isotopes(element)
                    for isotope, abundance in natural_isotopes.items():
                        # Each isotope gets element_fraction * its natural abundance
                        composition[element][isotope] = element_fraction * abundance

        elif sample.material_type:
            # Infer composition from material_type
            # Try to parse as element symbol
            element = sample.material_type.strip().capitalize()

            # Use natural isotopes for this element
            composition[element] = self._get_natural_isotopes(element)

        return composition

    def _get_natural_isotopes(self, element):
        """Get all natural isotopes for an element with their abundances

        Returns a dict of {isotope: fraction} for all natural isotopes
        """
        # First try PyNE if available
        if HAS_PYNE:
            try:
                from pyne import data as pyne_data, nucname

                # Get atomic number for element
                z_num = nucname.znum(element.upper())

                # Common mass numbers for each element (we check these)
                # This is a simple approach - could be improved by checking a wider range
                mass_range = range(max(1, z_num * 2 - 20), z_num * 3 + 20)

                natural_isotopes = {}
                for mass_num in mass_range:
                    try:
                        nuc_id = nucname.id(f"{element}-{mass_num}")
                        abundance = pyne_data.natural_abund(nuc_id)
                        if abundance > 1e-10:  # Only include isotopes with measurable abundance
                            isotope_name = f"{element}-{mass_num}"
                            natural_isotopes[isotope_name] = abundance
                    except:
                        continue

                # Return all natural isotopes with their abundances
                if natural_isotopes:
                    return natural_isotopes

            except Exception as e:
                logger.debug(f"PyNE lookup failed for {element}: {e}")

        # Fallback to SIMPLE_CROSS_SECTIONS database
        if element in SIMPLE_CROSS_SECTIONS:
            isotopes = SIMPLE_CROSS_SECTIONS[element]
            # Return all isotopes with their abundances (convert % to fraction)
            natural_isotopes = {}
            for isotope, data in isotopes.items():
                abundance_percent = data[0]  # First element is abundance percentage
                natural_isotopes[isotope] = abundance_percent / 100.0
            return natural_isotopes

        # Return unknown isotope as fallback
        return {f"{element}-Unknown": 1.0}

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

        # Get sample mass and convert to grams
        if sample.mass:
            mass_value = float(sample.mass)
            mass_unit = sample.mass_unit if sample.mass_unit else 'g'

            # Convert to grams
            if mass_unit == 'mg':
                mass_g = mass_value / 1000.0
            elif mass_unit == 'kg':
                mass_g = mass_value * 1000.0
            elif mass_unit == 'g':
                mass_g = mass_value
            else:
                logger.warning(f"Unknown mass unit: {mass_unit}, assuming grams")
                mass_g = mass_value
        else:
            mass_g = 1.0  # Default 1 gram

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

        # Calculate irradiation start/end times (make timezone-aware)
        irr_datetime = timezone.make_aware(datetime.combine(log.irradiation_date, log.time_in))
        irr_end_datetime = timezone.make_aware(datetime.combine(log.irradiation_date, log.time_out))

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

            # Deplete target by number of atoms consumed
            # For radioactive products: consumption = production + decay
            # For stable products: consumption = production
            # Simplified: assume consumption ≈ production (small depletion typically < 1%)
            n_consumed = n_produced if half_life_s == 'stable' else n_produced  # Could refine this
            new_inventory[target_isotope] = max(0, n_atoms - n_consumed)

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
            dict: {isotopes: {...}, stable_isotopes: {...}}
        """
        activities = {}
        stable_isotopes = {}
        total_activity = 0.0

        # Calculate activity for each isotope
        for isotope, n_atoms in inventory.items():
            if n_atoms <= 0:
                continue

            # Get half-life for this isotope (not cross-section - it might be a product!)
            half_life_s = self._get_half_life(isotope)

            # Track stable isotopes separately
            if half_life_s is None or half_life_s == 'stable' or half_life_s == 0:
                stable_isotopes[isotope] = {
                    'activity_bq': 0.0,
                    'activity_ci': 0.0,
                    'atoms': n_atoms,
                    'half_life_s': None,  # Use None instead of float('inf') for JSON serialization
                    'half_life_display': 'stable',
                    'fraction': 0.0,
                    'is_stable': True
                }
                continue

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
                    'is_stable': False
                }
                total_activity += activity_bq

        # Filter radioactive isotopes by minimum fraction
        filtered = {}
        for isotope, data in activities.items():
            fraction = data['activity_bq'] / total_activity if total_activity > 0 else 0
            if fraction >= min_fraction:
                data['fraction'] = fraction
                filtered[isotope] = data

        return {
            'isotopes': filtered,
            'stable_isotopes': stable_isotopes,
            'total_activity_bq': total_activity  # Return the true total before filtering
        }

    def _get_half_life(self, isotope):
        """
        Get half-life for an isotope from PyNE or fallback database

        Args:
            isotope: Isotope name (e.g., "Au-198")

        Returns:
            float: Half-life in seconds, or 'stable', or None if unknown
        """
        # Try PyNE first
        if HAS_PYNE:
            try:
                product_nucid = nucname.id(isotope)
                half_life_s = pyne_data.half_life(product_nucid)

                # PyNE returns inf for stable isotopes
                if half_life_s is None or half_life_s <= 0:
                    return 'stable'
                elif HAS_NUMPY and not np.isfinite(half_life_s):
                    return 'stable'

                return half_life_s
            except Exception as e:
                logger.debug(f"PyNE half-life lookup failed for {isotope}: {e}")

        # Fallback to simplified database
        try:
            element = isotope.split('-')[0]
        except (IndexError, AttributeError):
            return None

        if element in SIMPLE_CROSS_SECTIONS:
            # Check if this isotope is a product in our database
            for target_isotope, data in SIMPLE_CROSS_SECTIONS[element].items():
                product = data[2]  # product_isotope
                if product == isotope:
                    return data[3]  # half_life_s

        logger.debug(f"No half-life data found for {isotope}")
        return None

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
        Get neutron capture cross-section data using PyNE DataSource interface

        Uses proper energy-dependent cross sections with spectrum-weighted averaging.
        Supports multiple data sources: SimpleDataSource, EAFDataSource, and ENDF readers.

        Args:
            isotope: Isotope name (e.g., "Au-197")
            thermal_flux: Thermal neutron flux (n/cm²/s) for E < 0.5 eV
            fast_flux: Fast neutron flux (n/cm²/s) for E > 0.1 MeV
            intermediate_flux: Intermediate flux (n/cm²/s) for 0.5 eV < E < 0.1 MeV

        Returns:
            tuple: (sigma_barns, product_isotope, half_life_s) or None
        """
        try:
            from pyne.xs import data_source

            # Convert isotope name to PyNE format
            nucid = nucname.id(isotope)

            # Define energy group structure for spectrum collapse
            # Create a 3-group structure matching our flux definitions:
            # Group 1: Fast (10 MeV - 0.1 MeV)
            # Group 2: Intermediate/Epithermal (0.1 MeV - 0.5 eV)
            # Group 3: Thermal (0.5 eV - 1e-5 eV)
            if thermal_flux and fast_flux:
                # Energy boundaries in eV (high to low)
                # Use logarithmic spacing for better resolution across energy ranges
                E_g = np.array([
                    1.0e7,      # 10 MeV - upper bound for fast
                    1.0e5,      # 0.1 MeV - boundary between fast and intermediate
                    0.5,        # 0.5 eV - boundary between intermediate and thermal
                    1.0e-5      # Lower thermal cutoff
                ])

                # Flux weights for each group (in same order as energy boundaries)
                # Groups are defined between consecutive energy boundaries
                flux_weights = np.array([
                    fast_flux if fast_flux else 0.0,                      # Fast group
                    intermediate_flux if intermediate_flux else 0.0,      # Intermediate group
                    thermal_flux if thermal_flux else 0.0,                # Thermal group
                ])

                # Normalize flux weights
                total_flux_weight = np.sum(flux_weights)
                if total_flux_weight > 0:
                    flux_weights = flux_weights / total_flux_weight
                else:
                    # Fallback: equal weighting
                    flux_weights = np.ones(3) / 3.0

                logger.debug(f"Energy groups (eV): {E_g}")
                logger.debug(f"Flux weights: fast={flux_weights[0]:.3f}, "
                           f"inter={flux_weights[1]:.3f}, thermal={flux_weights[2]:.3f}")
            else:
                # No flux spectrum - use default thermal spectrum
                E_g = None
                flux_weights = None

            # Try multiple data sources in order of preference
            data_sources = []

            # 1. Try SimpleDataSource first (uses physical models, works for common isotopes)
            try:
                if E_g is not None:
                    sds = data_source.SimpleDataSource(dst_group_struct=E_g)
                else:
                    sds = data_source.SimpleDataSource()
                data_sources.append(('Simple', sds))
            except Exception as e:
                logger.debug(f"SimpleDataSource initialization failed: {e}")

            # 2. Try EAFDataSource (European Activation File - good for activation)
            try:
                if E_g is not None:
                    eds = data_source.EAFDataSource(dst_group_struct=E_g)
                else:
                    eds = data_source.EAFDataSource()
                data_sources.append(('EAF', eds))
            except Exception as e:
                logger.debug(f"EAFDataSource initialization failed: {e}")

            # 3. Could add CinderDataSource or OpenMCDataSource if available
            # try:
            #     cds = data_source.CinderDataSource(dst_group_struct=E_g)
            #     data_sources.append(('Cinder', cds))
            # except:
            #     pass

            # Try each data source for (n,gamma) reaction
            sigma_barns = None
            source_name = None

            for name, ds in data_sources:
                try:
                    # Get (n,gamma) cross section data
                    # PyNE reactions: 'gamma' = (n,gamma), 'absorption' = total absorption
                    if E_g is not None and flux_weights is not None:
                        # Get multi-group cross sections and collapse using flux weighting
                        xs_mg = ds.discretize(nucid, 'gamma')

                        if xs_mg is not None and len(xs_mg) > 0:
                            # Flux-weighted collapse to one-group cross section
                            # σ_collapsed = Σ(σ_g × φ_g) / Σ(φ_g)
                            # Since flux_weights are already normalized, just multiply and sum

                            # Handle case where xs_mg might be longer than flux_weights
                            # (e.g., if data source has more groups)
                            n_groups = min(len(xs_mg), len(flux_weights))
                            sigma_barns = np.sum(xs_mg[:n_groups] * flux_weights[:n_groups])

                            logger.debug(f"{name} multi-group XS for {isotope}: {xs_mg[:n_groups]} barns")
                            logger.debug(f"Spectrum-averaged σ = {sigma_barns:.3f} barns")
                            source_name = name
                            break
                    else:
                        # No flux spectrum - get thermal cross section
                        xs_data = ds.reaction(nucid, 'gamma')

                        if xs_data and 'xs' in xs_data:
                            # For thermal, use the lowest energy cross section
                            xs_array = xs_data['xs']
                            if len(xs_array) > 0:
                                sigma_barns = xs_array[-1]  # Last value is lowest energy (thermal)
                                logger.debug(f"{name} thermal XS for {isotope}: {sigma_barns:.3f} barns")
                                source_name = name
                                break

                except Exception as e:
                    logger.debug(f"{name} DataSource failed for {isotope}: {e}")
                    continue

            if sigma_barns is None or sigma_barns <= 0:
                logger.debug(f"No cross-section data found for {isotope} in any PyNE data source")
                return None

            # Determine product isotope (n,gamma adds one neutron: A -> A+1)
            element_z = nucname.znum(nucid)
            mass_a = nucname.anum(nucid)
            product_nucid = nucname.id(element_z * 1000 + mass_a + 1)

            # Format product isotope name (e.g., "Au-198")
            try:
                product_name = nucname.name(product_nucid)
                # Convert PyNE format to our format if needed
                # PyNE might return "Au198" or "Au-198"
                if '-' not in product_name:
                    element_sym = nucname.name(element_z * 1000).capitalize()
                    product_isotope = f"{element_sym}-{mass_a + 1}"
                else:
                    product_isotope = product_name
            except:
                # Fallback: construct manually
                element_sym = nucname.name(element_z * 1000).capitalize()
                product_isotope = f"{element_sym}-{mass_a + 1}"

            # Get half-life of product isotope
            try:
                half_life_s = pyne_data.half_life(product_nucid)
                if half_life_s is None or half_life_s <= 0:
                    half_life_s = 'stable'
                elif HAS_NUMPY and not np.isfinite(half_life_s):
                    half_life_s = 'stable'
            except:
                # Try decay constant as fallback
                try:
                    decay_const = pyne_data.decay_const(product_nucid)
                    if decay_const > 0 and np.isfinite(decay_const):
                        half_life_s = LAMBDA_LN2 / decay_const
                    else:
                        half_life_s = 'stable'
                except:
                    half_life_s = 'stable'

            logger.info(f"PyNE {source_name} data for {isotope}: σ={sigma_barns:.3f}b, "
                       f"product={product_isotope}, t½={half_life_s}")

            return (sigma_barns, product_isotope, half_life_s)

        except Exception as e:
            logger.debug(f"PyNE cross-section lookup failed for {isotope}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def _get_gamma_energies(self, isotope):
        """
        Get gamma energies and intensities for an isotope from PyNE

        Args:
            isotope: Isotope name (e.g., "Co-60", "Au-198")

        Returns:
            float: Weighted average gamma energy in MeV, or None if no gamma data
        """
        if not HAS_PYNE:
            return None

        try:
            from pyne import data as pyne_data, nucname

            # Convert isotope name to PyNE nucid
            nuc_id = nucname.id(isotope)

            # Get gamma energies and intensities
            # PyNE returns lists of tuples: [(value, uncertainty), ...]
            try:
                # Try to get gamma ray data from PyNE
                intensities = pyne_data.gamma_photon_intensity(nuc_id)
                energies = pyne_data.gamma_energy(nuc_id)

                if intensities and energies and len(intensities) > 0 and len(energies) > 0:
                    # Calculate weighted average energy
                    # intensities is [(intensity, uncertainty), ...]
                    # energies is [(energy_keV, uncertainty), ...]
                    total_intensity = sum(inten[0] for inten in intensities)
                    if total_intensity > 0 and len(intensities) == len(energies):
                        # Weighted average: Σ(E_i × I_i) / Σ(I_i)
                        weighted_energy_kev = sum(energies[i][0] * intensities[i][0]
                                                 for i in range(len(energies))) / total_intensity
                        # Convert from keV to MeV
                        weighted_energy_mev = weighted_energy_kev / 1000.0
                        logger.debug(f"Gamma energy for {isotope}: {weighted_energy_mev:.3f} MeV (avg from {len(energies)} gammas)")
                        return weighted_energy_mev
            except (AttributeError, KeyError):
                # PyNE doesn't have gamma_photon_intensity, try alternative
                # Use decay gamma data if available
                try:
                    # Get ecorr data (gamma energies)
                    ecorr = pyne_data.ecorr(nuc_id)
                    if ecorr and ecorr > 0:
                        # ecorr is average gamma energy per decay in MeV
                        logger.debug(f"Gamma energy for {isotope}: {ecorr:.3f} MeV (ecorr)")
                        return ecorr
                except:
                    pass

        except Exception as e:
            logger.debug(f"Could not get gamma energies for {isotope}: {e}")

        return None

    def _estimate_dose_rate(self, isotopes):
        """
        Estimate dose rate at 1 foot using isotope-specific gamma energies

        Uses "6 C E rule": dose rate (mrem/hr) ≈ 6 × C × E_avg
        where:
            C = activity in Curies
            E_avg = average gamma energy in MeV
            6 = conversion factor for point source at 1 foot

        For isotopes without gamma data, uses fallback scaling factor.

        Args:
            isotopes: dict of isotopes with activities

        Returns:
            float: estimated dose rate in mrem/hr at 1 foot
        """
        print(f"=== DOSE RATE CALCULATION CALLED ===")
        print(f"Number of isotopes: {len(isotopes)}")

        total_dose_rate = 0.0
        isotopes_with_gamma = 0
        isotopes_without_gamma = 0

        for isotope_name, isotope_data in isotopes.items():
            activity_ci = isotope_data['activity_ci']
            print(f"Processing {isotope_name}: activity_ci = {activity_ci}")

            if activity_ci <= 0:
                continue

            # Get gamma energy for this isotope
            gamma_energy_mev = self._get_gamma_energies(isotope_name)

            import sys
            sys.stderr.write(f"DEBUG: {isotope_name} gamma_energy_mev = {gamma_energy_mev}\n")
            sys.stderr.flush()

            if gamma_energy_mev and gamma_energy_mev > 0:
                # Use 6 C E rule for gamma emitters
                dose_contribution = 6.0 * activity_ci * gamma_energy_mev
                isotopes_with_gamma += 1
                sys.stderr.write(f"DEBUG: {isotope_name}: 6 × {activity_ci:.2e} Ci × {gamma_energy_mev:.3f} MeV = {dose_contribution:.6f} mrem/hr\n")
                sys.stderr.flush()
                logger.debug(f"{isotope_name}: {activity_ci:.2e} Ci × {gamma_energy_mev:.3f} MeV = {dose_contribution:.2f} mrem/hr")
            else:
                # Fallback for isotopes without gamma data (beta emitters, or missing data)
                # Use conservative estimate: 1 Ci ≈ 500 mrem/hr (lower than gamma emitters)
                dose_contribution = activity_ci * 500.0
                isotopes_without_gamma += 1
                logger.debug(f"{isotope_name}: No gamma data, using fallback ({dose_contribution:.2f} mrem/hr)")

            total_dose_rate += dose_contribution

        import sys
        sys.stdout.flush()
        sys.stderr.write(f"\n\n*** DOSE RATE CALCULATION COMPLETE ***\n")
        sys.stderr.write(f"*** Total dose rate: {total_dose_rate:.2f} mrem/hr ***\n")
        sys.stderr.write(f"*** Isotopes with gamma: {isotopes_with_gamma}, without: {isotopes_without_gamma} ***\n\n")
        sys.stderr.flush()

        logger.info(f"Dose rate calculation: {isotopes_with_gamma} isotopes with gamma data, "
                   f"{isotopes_without_gamma} using fallback. Total: {total_dose_rate:.2f} mrem/hr")

        return total_dose_rate
