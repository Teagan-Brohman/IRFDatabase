#!/usr/bin/env python
"""
Test script for enhanced decay timeline tracking

Demonstrates:
1. Current behavior (final state only)
2. Enhanced tracking of activity after each irradiation step
3. Decay to current date
4. Time-series decay curves
5. Activity at arbitrary future dates
"""

import sys
import os
from datetime import datetime, timedelta

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter


def create_sample_irradiation_data():
    """
    Create sample data for a gold foil with multiple irradiations

    Scenario: Au-197 foil irradiated 3 times over several months
    """
    from datetime import time

    # Sample: 1 gram gold foil (Au-197, 100% natural abundance)
    sample_data = {
        'mass_g': 1.0,
        'composition': {
            'Au': {
                'Au-197': 1.0  # 100% Au-197
            }
        }
    }

    # Three irradiations at different times
    irradiations = [
        {
            'date': datetime(2024, 1, 15),
            'time_in': time(10, 0),
            'time_out': time(14, 0),  # 4 hours
            'power_kw': 200.0,
            'location': 'bare_rabbit',
            'description': 'First activation'
        },
        {
            'date': datetime(2024, 3, 1),  # 46 days later
            'time_in': time(9, 0),
            'time_out': time(11, 0),  # 2 hours
            'power_kw': 200.0,
            'location': 'bare_rabbit',
            'description': 'Second activation (after Au-198 mostly decayed)'
        },
        {
            'date': datetime(2024, 5, 10),  # 70 days after second
            'time_in': time(13, 0),
            'time_out': time(17, 0),  # 4 hours
            'power_kw': 200.0,
            'location': 'bare_rabbit',
            'description': 'Third activation'
        }
    ]

    # Flux configuration (typical thermal reactor)
    flux_config = {
        'thermal_flux': 2.5e12,  # n/cm²/s
        'fast_flux': 1.0e11,     # n/cm²/s
        'intermediate_flux': 5.0e10,  # n/cm²/s
        'reference_power': 200.0  # kW
    }

    return sample_data, irradiations, flux_config


def simulate_enhanced_activation(sample_data, irradiations, flux_config):
    """
    Simulate activation with detailed tracking of intermediate states

    Returns timeline of activities after each step
    """
    # Using simplified model (no PyNE required for this demonstration)
    HAS_LIBS = True

    # Initialize inventory
    N_A = 6.022e23
    mass_g = sample_data['mass_g']

    # Au-197: mass number = 197
    n_atoms_Au197 = (mass_g * N_A) / 197.0

    # Track timeline: list of (datetime, inventory, description)
    timeline = []

    # Initial state
    inventory = {'Au-197': n_atoms_Au197}
    timeline.append({
        'datetime': irradiations[0]['date'] - timedelta(days=1),
        'inventory': inventory.copy(),
        'description': 'Initial state (before any irradiation)',
        'step': 0
    })

    # Cross section for Au-197 (n,gamma) -> Au-198
    # Thermal: ~98.65 barns, product half-life: 2.6955 days
    sigma_thermal = 98.65  # barns
    sigma_cm2 = sigma_thermal * 1e-24  # convert to cm²
    t_half_Au198 = 2.6955 * 24 * 3600  # seconds
    lambda_Au198 = 0.693147 / t_half_Au198

    current_inventory = inventory.copy()
    previous_time = None

    for idx, irr in enumerate(irradiations, start=1):
        # Get irradiation times
        irr_start = datetime.combine(irr['date'], irr['time_in'])
        irr_end = datetime.combine(irr['date'], irr['time_out'])
        irr_duration_s = (irr_end - irr_start).total_seconds()

        # Decay from previous irradiation to this one
        if previous_time:
            decay_time_s = (irr_start - previous_time).total_seconds()

            # Decay Au-198 (Au-197 is stable)
            if 'Au-198' in current_inventory:
                n_Au198_before = current_inventory['Au-198']
                n_Au198_after = n_Au198_before * np.exp(-lambda_Au198 * decay_time_s)
                current_inventory['Au-198'] = n_Au198_after

                timeline.append({
                    'datetime': irr_start - timedelta(seconds=1),
                    'inventory': current_inventory.copy(),
                    'description': f'After decay period ({decay_time_s/86400:.1f} days)',
                    'step': f'{idx}a',
                    'decay_time_days': decay_time_s / 86400
                })

        # Activation during irradiation
        flux = flux_config['thermal_flux']  # Use thermal flux for Au-197
        n_Au197 = current_inventory.get('Au-197', 0)

        # Production rate: R = σ × φ × N
        production_rate = sigma_cm2 * flux * n_Au197  # atoms/s

        # Saturation formula: N_product = (R/λ) * [1 - exp(-λt)]
        n_produced = (production_rate / lambda_Au198) * (1 - np.exp(-lambda_Au198 * irr_duration_s))

        # Update inventory
        current_inventory['Au-198'] = current_inventory.get('Au-198', 0) + n_produced
        # Au-197 depletion is negligible (<< 1%)

        timeline.append({
            'datetime': irr_end,
            'inventory': current_inventory.copy(),
            'description': f'{irr["description"]} complete',
            'step': idx,
            'irradiation_hours': irr_duration_s / 3600,
            'atoms_produced': n_produced
        })

        previous_time = irr_end

    # Decay to current date
    current_date = datetime.now()
    if previous_time and current_date > previous_time:
        decay_time_s = (current_date - previous_time).total_seconds()

        if 'Au-198' in current_inventory:
            n_Au198_before = current_inventory['Au-198']
            n_Au198_after = n_Au198_before * np.exp(-lambda_Au198 * decay_time_s)
            current_inventory['Au-198'] = n_Au198_after

            timeline.append({
                'datetime': current_date,
                'inventory': current_inventory.copy(),
                'description': f'Decayed to current date ({decay_time_s/86400:.1f} days after last irradiation)',
                'step': 'current',
                'decay_time_days': decay_time_s / 86400
            })

    return timeline, t_half_Au198, lambda_Au198


def calculate_activities(timeline_entry, lambda_Au198):
    """Calculate activities (Bq) from inventory"""
    inventory = timeline_entry['inventory']

    activities = {}
    for isotope, n_atoms in inventory.items():
        if isotope == 'Au-198':
            # Activity = λ × N
            activity_bq = lambda_Au198 * n_atoms
            activity_ci = activity_bq / 3.7e10
            activity_mci = activity_ci * 1000

            activities[isotope] = {
                'atoms': n_atoms,
                'activity_bq': activity_bq,
                'activity_ci': activity_ci,
                'activity_mci': activity_mci
            }
        elif isotope == 'Au-197':
            # Stable - no activity
            activities[isotope] = {
                'atoms': n_atoms,
                'activity_bq': 0,
                'activity_ci': 0,
                'activity_mci': 0
            }

    return activities


def print_timeline(timeline, lambda_Au198):
    """Print activity timeline in readable format"""
    print("\n" + "=" * 100)
    print(" Activity Timeline - Au-197 Sample with Multiple Irradiations")
    print("=" * 100)

    for entry in timeline:
        dt = entry['datetime']
        desc = entry['description']
        step = entry['step']

        activities = calculate_activities(entry, lambda_Au198)

        au198_activity = activities.get('Au-198', {}).get('activity_mci', 0)
        au198_atoms = activities.get('Au-198', {}).get('atoms', 0)

        print(f"\nStep {step}: {dt.strftime('%Y-%m-%d %H:%M')}")
        print(f"  {desc}")

        if 'decay_time_days' in entry:
            print(f"  Decay time: {entry['decay_time_days']:.2f} days")

        if 'irradiation_hours' in entry:
            print(f"  Irradiation duration: {entry['irradiation_hours']:.2f} hours")

        if 'atoms_produced' in entry:
            print(f"  Atoms produced: {entry['atoms_produced']:.3e}")

        print(f"  Au-198 Inventory: {au198_atoms:.3e} atoms")
        print(f"  Au-198 Activity: {au198_activity:.3f} mCi ({au198_activity*1000:.1f} µCi)")

        # Show other isotopes if present
        for isotope, data in activities.items():
            if isotope != 'Au-198':
                print(f"  {isotope}: {data['atoms']:.3e} atoms (stable)")


def generate_decay_curves(timeline, lambda_Au198, t_half_Au198):
    """Generate decay curves showing activity evolution"""
    # Create time points from first to last timeline entry plus some future
    start_time = timeline[0]['datetime']
    end_time = timeline[-1]['datetime']

    # Extend to several half-lives beyond current date
    extended_end = end_time + timedelta(days=t_half_Au198 / 86400 * 5)

    # Find each irradiation end time in timeline
    irradiation_events = [e for e in timeline if 'irradiation_hours' in e]

    # Generate continuous decay curve
    time_points = []
    activity_points = []

    # For each segment between events, calculate decay
    for i in range(len(timeline) - 1):
        current_event = timeline[i]
        next_event = timeline[i + 1]

        # Get Au-198 inventory at current event
        n_Au198_start = current_event['inventory'].get('Au-198', 0)

        # Time range for this segment
        t_start = current_event['datetime']
        t_end = next_event['datetime']

        # Generate points
        num_points = 50
        for j in range(num_points):
            t_delta_s = (t_end - t_start).total_seconds() * j / num_points
            t = t_start + timedelta(seconds=t_delta_s)

            # Decay from start of segment
            n_Au198 = n_Au198_start * np.exp(-lambda_Au198 * t_delta_s)
            activity_bq = lambda_Au198 * n_Au198
            activity_mci = (activity_bq / 3.7e10) * 1000

            time_points.append(t)
            activity_points.append(activity_mci)

    # Extend beyond last point
    last_event = timeline[-1]
    n_Au198_final = last_event['inventory'].get('Au-198', 0)
    t_final = last_event['datetime']

    for days in range(0, 30, 1):  # Extend 30 days
        t = t_final + timedelta(days=days)
        t_delta_s = days * 86400
        n_Au198 = n_Au198_final * np.exp(-lambda_Au198 * t_delta_s)
        activity_bq = lambda_Au198 * n_Au198
        activity_mci = (activity_bq / 3.7e10) * 1000

        time_points.append(t)
        activity_points.append(activity_mci)

    # Create plot
    fig, ax = plt.subplots(figsize=(14, 8))

    ax.plot(time_points, activity_points, 'b-', linewidth=2, label='Au-198 Activity')

    # Mark irradiation events
    for event in irradiation_events:
        t = event['datetime']
        activities = calculate_activities(event, lambda_Au198)
        activity_mci = activities['Au-198']['activity_mci']

        ax.plot(t, activity_mci, 'ro', markersize=10, label=f"After Irradiation {event['step']}")
        ax.axvline(t, color='red', linestyle='--', alpha=0.3)

    # Mark current date
    current_event = [e for e in timeline if e['step'] == 'current']
    if current_event:
        t_current = current_event[0]['datetime']
        activities_current = calculate_activities(current_event[0], lambda_Au198)
        activity_current = activities_current['Au-198']['activity_mci']

        ax.plot(t_current, activity_current, 'g^', markersize=12, label='Current Date', zorder=5)
        ax.axvline(t_current, color='green', linestyle='--', alpha=0.5)

    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Au-198 Activity (mCi)', fontsize=12)
    ax.set_title('Au-197 Foil Activation Timeline\n(Multiple Irradiations with Decay Periods)', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')

    # Format x-axis
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)

    # Use log scale for y-axis to see decay
    ax.set_yscale('log')

    plt.tight_layout()
    plt.savefig('/home/user/IRFDatabase/decay_timeline.png', dpi=150)
    print(f"\nDecay curve saved to: /home/user/IRFDatabase/decay_timeline.png")

    return fig


def main():
    """Run decay timeline demonstration"""
    print("\n" + "=" * 100)
    print(" Decay Timeline Demonstration")
    print("=" * 100)

    # Create sample data
    print("\nCreating sample irradiation scenario...")
    sample_data, irradiations, flux_config = create_sample_irradiation_data()

    print(f"\nSample: {sample_data['mass_g']} g Au-197 foil")
    print(f"Number of irradiations: {len(irradiations)}")

    for idx, irr in enumerate(irradiations, start=1):
        duration_hr = (datetime.combine(irr['date'], irr['time_out']) -
                      datetime.combine(irr['date'], irr['time_in'])).total_seconds() / 3600
        print(f"  {idx}. {irr['date'].strftime('%Y-%m-%d')}: {duration_hr:.1f} hours at {irr['power_kw']} kW")

    # Run enhanced simulation
    print("\nRunning enhanced activation simulation...")
    result = simulate_enhanced_activation(sample_data, irradiations, flux_config)

    if result is None:
        print("ERROR: Required libraries not available")
        return 1

    timeline, t_half_Au198, lambda_Au198 = result

    # Print timeline
    print_timeline(timeline, lambda_Au198)

    # Generate decay curves
    print("\n" + "=" * 100)
    print("Generating decay curve plot...")
    print("=" * 100)

    try:
        generate_decay_curves(timeline, lambda_Au198, t_half_Au198)
        print("\n✓ Plot generated successfully")
    except Exception as e:
        print(f"\n✗ Plot generation failed: {e}")
        import traceback
        traceback.print_exc()

    # Summary
    print("\n" + "=" * 100)
    print(" Key Observations")
    print("=" * 100)

    print("\n1. Activity Evolution:")
    print("   - Activity builds up during each irradiation")
    print("   - Activity decays between irradiations (Au-198 t½ = 2.70 days)")
    print("   - Each subsequent irradiation starts with lower activity than previous peak")

    print("\n2. Current State:")
    current_entry = [e for e in timeline if e['step'] == 'current'][0]
    current_activity = calculate_activities(current_entry, lambda_Au198)
    print(f"   - Current Au-198 activity: {current_activity['Au-198']['activity_mci']:.3f} mCi")
    print(f"   - Days since last irradiation: {current_entry['decay_time_days']:.1f}")

    print("\n3. Decay Periods:")
    decay_entries = [e for e in timeline if 'decay_time_days' in e]
    for e in decay_entries[:-1]:  # Exclude current date
        print(f"   - {e['description']}: {e['decay_time_days']:.1f} days")

    print("\n" + "=" * 100)
    print(" Feature Suggestions for Implementation")
    print("=" * 100)

    print("""
1. DATABASE STORAGE:
   - Add 'ActivationTimeline' model to store intermediate states
   - Fields: sample, step_number, datetime, inventory_json, description
   - Link to parent ActivationResult

2. API ENDPOINTS:
   - /api/sample/<pk>/activation-timeline/  → Full timeline with all steps
   - /api/sample/<pk>/activity-at/<date>/   → Activity at specific date
   - /api/sample/<pk>/decay-curve/          → Time-series data for plotting

3. UI FEATURES:
   - Timeline view: Show activity after each irradiation step
   - Decay calculator: "What will activity be on [future date]?"
   - Interactive plot: Plotly timeline with markers for each irradiation
   - Step-through: Navigate through irradiation history step-by-step
   - Export: CSV/Excel of complete timeline

4. CALCULATION OPTIONS:
   - Calculate to arbitrary date (past or future)
   - Show decay from any intermediate point
   - Compare "what if" scenarios (e.g., different decay times)
   - Batch calculate activities for multiple future dates

5. DISPLAY OPTIONS:
   - Table: Date | Step | Activity | Isotopes
   - Graph: Activity vs time with event markers
   - Summary: Peak activity, current activity, half-lives decayed
   - Warnings: "Activity below detection limit after X days"
    """)

    print("\n" + "=" * 100)

    return 0


if __name__ == '__main__':
    sys.exit(main())
