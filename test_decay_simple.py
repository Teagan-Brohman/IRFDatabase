#!/usr/bin/env python3
"""
Simplified decay timeline demonstration (no external dependencies)

Shows what features could be added for tracking activation/decay timeline
"""

from datetime import datetime, timedelta
import math


def main():
    print("\n" + "="*100)
    print(" DECAY TIMELINE DEMONSTRATION - Enhanced Activation Tracking")
    print("="*100)

    print("""
SCENARIO: 1 gram Au-197 foil with 3 irradiations over several months
- Irradiation 1: 2024-01-15, 4 hours at 200 kW
- Irradiation 2: 2024-03-01 (46 days later), 2 hours at 200 kW
- Irradiation 3: 2024-05-10 (70 days later), 4 hours at 200 kW

Nuclear data:
- Au-197 (n,γ) Au-198: σ = 98.65 barns (thermal)
- Au-198 half-life: 2.6955 days
- Thermal flux: 2.5×10¹² n/cm²/s
    """)

    # Parameters
    N_A = 6.022e23
    mass_g = 1.0
    sigma_barns = 98.65
    sigma_cm2 = sigma_barns * 1e-24
    flux = 2.5e12  # n/cm²/s
    t_half = 2.6955 * 24 * 3600  # seconds
    lambda_decay = 0.693147 / t_half

    # Initial Au-197 atoms
    n_Au197 = (mass_g * N_A) / 197.0
    production_rate = sigma_cm2 * flux * n_Au197

    # Timeline tracking
    timeline = []

    # Initial state
    timeline.append({
        'date': '2024-01-14',
        'step': 'Initial',
        'Au198_atoms': 0,
        'activity_mCi': 0,
        'description': 'Before any irradiation'
    })

    n_Au198 = 0  # Start with no Au-198

    # Irradiation 1: 4 hours
    irr1_time_s = 4 * 3600
    n_produced_1 = (production_rate / lambda_decay) * (1 - math.exp(-lambda_decay * irr1_time_s))
    n_Au198 += n_produced_1
    activity_1 = (lambda_decay * n_Au198) / 3.7e10 * 1000  # mCi

    timeline.append({
        'date': '2024-01-15 14:00',
        'step': '1 (end)',
        'Au198_atoms': n_Au198,
        'activity_mCi': activity_1,
        'description': 'After 4-hour irradiation #1'
    })

    # Decay period 1: 46 days
    decay1_s = 46 * 24 * 3600
    n_Au198 *= math.exp(-lambda_decay * decay1_s)
    activity_decay1 = (lambda_decay * n_Au198) / 3.7e10 * 1000

    timeline.append({
        'date': '2024-03-01 09:00',
        'step': '1→2 decay',
        'Au198_atoms': n_Au198,
        'activity_mCi': activity_decay1,
        'description': 'After 46-day decay (17 half-lives!)'
    })

    # Irradiation 2: 2 hours
    irr2_time_s = 2 * 3600
    n_produced_2 = (production_rate / lambda_decay) * (1 - math.exp(-lambda_decay * irr2_time_s))
    n_Au198 += n_produced_2
    activity_2 = (lambda_decay * n_Au198) / 3.7e10 * 1000

    timeline.append({
        'date': '2024-03-01 11:00',
        'step': '2 (end)',
        'Au198_atoms': n_Au198,
        'activity_mCi': activity_2,
        'description': 'After 2-hour irradiation #2'
    })

    # Decay period 2: 70 days
    decay2_s = 70 * 24 * 3600
    n_Au198 *= math.exp(-lambda_decay * decay2_s)
    activity_decay2 = (lambda_decay * n_Au198) / 3.7e10 * 1000

    timeline.append({
        'date': '2024-05-10 13:00',
        'step': '2→3 decay',
        'Au198_atoms': n_Au198,
        'activity_mCi': activity_decay2,
        'description': 'After 70-day decay (26 half-lives!)'
    })

    # Irradiation 3: 4 hours
    irr3_time_s = 4 * 3600
    n_produced_3 = (production_rate / lambda_decay) * (1 - math.exp(-lambda_decay * irr3_time_s))
    n_Au198 += n_produced_3
    activity_3 = (lambda_decay * n_Au198) / 3.7e10 * 1000

    timeline.append({
        'date': '2024-05-10 17:00',
        'step': '3 (end)',
        'Au198_atoms': n_Au198,
        'activity_mCi': activity_3,
        'description': 'After 4-hour irradiation #3'
    })

    # Decay to current date
    last_irr = datetime(2024, 5, 10, 17, 0)
    current = datetime.now()
    decay_to_current_s = (current - last_irr).total_seconds()
    n_Au198 *= math.exp(-lambda_decay * decay_to_current_s)
    activity_current = (lambda_decay * n_Au198) / 3.7e10 * 1000

    timeline.append({
        'date': current.strftime('%Y-%m-%d %H:%M'),
        'step': 'CURRENT',
        'Au198_atoms': n_Au198,
        'activity_mCi': activity_current,
        'description': f'Current date ({(decay_to_current_s/86400):.0f} days after last irradiation)'
    })

    # Print timeline
    print("\n" + "="*100)
    print(" ACTIVITY TIMELINE")
    print("="*100)
    print(f"\n{'Date':<20} {'Step':<15} {'Au-198 Atoms':<20} {'Activity':<15} {'Description'}")
    print("-"*100)

    for entry in timeline:
        atoms_str = f"{entry['Au198_atoms']:.2e}" if entry['Au198_atoms'] > 0 else "0"
        activity_str = f"{entry['activity_mCi']:.3f} mCi" if entry['activity_mCi'] > 0.001 else "< 0.001 mCi"

        print(f"{entry['date']:<20} {entry['step']:<15} {atoms_str:<20} {activity_str:<15} {entry['description']}")

    # Analysis
    print("\n" + "="*100)
    print(" KEY OBSERVATIONS")
    print("="*100)

    print(f"""
1. DECAY BETWEEN IRRADIATIONS:
   - After 46 days (17 half-lives): Activity drops to {(activity_decay1/activity_1)*100:.2e}% of peak
   - After 70 days (26 half-lives): Activity drops to {(activity_decay2/activity_2)*100:.2e}% of peak
   - Long decay periods mean each irradiation essentially starts "fresh"

2. PEAK ACTIVITIES:
   - Irradiation #1 (4 hr): {activity_1:.2f} mCi
   - Irradiation #2 (2 hr): {activity_2:.2f} mCi  (lower - shorter time)
   - Irradiation #3 (4 hr): {activity_3:.2f} mCi  (similar to #1)

3. CURRENT ACTIVITY:
   - {activity_current:.3f} mCi ({(decay_to_current_s/86400):.0f} days after last irradiation)
   - Activity is {'detectable' if activity_current > 0.001 else 'below detection limit'}

4. SATURATION:
   - 4-hour irradiation reaches {(1 - math.exp(-lambda_decay * 4*3600))*100:.1f}% of saturation
   - Saturation activity would be: {(production_rate / lambda_decay * lambda_decay) / 3.7e10 * 1000:.2f} mCi
    """)

    print("\n" + "="*100)
    print(" WHAT THE CURRENT CODE DOES vs WHAT IT COULD DO")
    print("="*100)

    print("""
CURRENT IMPLEMENTATION:
✓ Applies activation during each irradiation
✓ Applies decay BETWEEN irradiations
✓ Returns final inventory at end of last irradiation
✓ Calculates total activity at that reference time

MISSING FEATURES:
✗ No record of intermediate states (activity after each step)
✗ No decay to current date (stops at last irradiation)
✗ No time-series data for plotting
✗ Cannot query "what's the activity on [specific date]?"
✗ No step-by-step timeline view
    """)

    print("\n" + "="*100)
    print(" PROPOSED ENHANCEMENTS")
    print("="*100)

    print("""
1. TIMELINE TRACKING:
   • Save inventory snapshot after each irradiation step
   • Save inventory after each decay period
   • Store in new ActivationTimeline model:
     - sample_id, step_number, datetime, inventory_json, description
     - activity_bq, dominant_isotopes, dose_rate_estimate

2. DECAY TO CURRENT DATE:
   • Automatically calculate activity at datetime.now()
   • Display "Current Activity" prominently in UI
   • Show days elapsed since last irradiation
   • Warning if activity below detection limit

3. ARBITRARY DATE QUERIES:
   • API endpoint: /api/sample/<pk>/activity-at/?date=2025-06-15
   • Form input: "Calculate activity on [date picker]"
   • Batch calculate for multiple dates (e.g., every 7 days for next year)

4. VISUALIZATION:
   • Interactive Plotly timeline with:
     - Activity vs time curve
     - Markers for each irradiation event
     - Shaded regions for decay periods
     - Vertical line for current date
     - Hover tooltips with isotope breakdown
   • Log scale y-axis to see full decay range
   • Option to show individual isotopes or total activity

5. USER INTERFACE:
   • Tab on sample detail page: "Activation Timeline"
   • Table showing:
     ┌─────────┬──────────────────┬─────────────────────┬──────────────┐
     │ Step    │ Date/Time        │ Activity            │ Description  │
     ├─────────┼──────────────────┼─────────────────────┼──────────────┤
     │ Initial │ 2024-01-14       │ 0 mCi               │ Before irr.  │
     │ 1       │ 2024-01-15 14:00 │ 45.23 mCi          │ After irr #1 │
     │ Decay   │ 2024-03-01 09:00 │ 0.0001 mCi (decay) │ 46 days      │
     │ 2       │ 2024-03-01 11:00 │ 22.61 mCi          │ After irr #2 │
     │ ...     │ ...              │ ...                 │ ...          │
     │ CURRENT │ 2025-11-16       │ 0.003 mCi          │ Current      │
     └─────────┴──────────────────┴─────────────────────┴──────────────┘

   • "Calculate Activity On Date" widget:
     - Date picker
     - "Calculate" button
     - Shows: activity, dose rate, isotope breakdown

   • Export options:
     - CSV: Full timeline with all isotopes
     - Excel: Multiple sheets (timeline, isotopes, parameters)
     - PDF: Report with timeline table + decay curve

6. ADVANCED FEATURES:
   • "What If" scenarios:
     - "What if I irradiate again on [date] for [time]?"
     - Compare multiple scenarios side-by-side
   • Dose planning:
     - "When will activity drop below [threshold]?"
     - "When is it safe to handle without shielding?"
   • Isotope filtering:
     - Show/hide specific isotopes
     - Filter by half-life range
     - Filter by minimum activity fraction
    """)

    print("\n" + "="*100)
    print(" QUESTIONS FOR YOU:")
    print("="*100)

    print("""
1. UI PREFERENCES:
   • Where should timeline be displayed?
     [ ] New tab on sample detail page
     [ ] Expandable section below current results
     [ ] Separate "Timeline" button that opens modal
     [ ] All of the above (different views for different use cases)

2. DEFAULT BEHAVIOR:
   • Should system automatically calculate to current date?
     [ ] Yes, always show current activity
     [ ] No, stop at last irradiation (current behavior)
     [ ] User preference/setting

3. GRANULARITY:
   • How detailed should timeline be?
     [ ] Every irradiation endpoint only
     [ ] Every irradiation + every decay period
     [ ] Every irradiation + decay to current + user-specified dates
     [ ] Generate time-series with N points per decay period

4. STORAGE:
   • Should all intermediate states be saved to database?
     [ ] Yes, save everything (enables fast queries but uses more space)
     [ ] No, calculate on-demand (slower but uses less space)
     [ ] Hybrid: save key snapshots, interpolate between them

5. VISUALIZATION PRIORITY:
   • What's most important to show?
     [ ] Total activity over time
     [ ] Individual isotope activities
     [ ] Dose rate over time
     [ ] Isotope composition (atoms) over time
     [ ] All of the above (multiple plot options)

6. SPECIFIC FEATURES YOU NEED:
   • Do you need to compare multiple samples?
   • Do you need to export timeline data?
   • Do you need "what if" scenario planning?
   • Do you need automated alerts (e.g., "activity below threshold")?
    """)

    print("\n" + "="*100)
    print(" IMPLEMENTATION COMPLEXITY:")
    print("="*100)

    print("""
EASY (1-2 hours):
✓ Modify calculate_activation() to return intermediate states
✓ Add decay_to_date() method
✓ Display timeline in simple table format

MEDIUM (4-8 hours):
✓ Add ActivationTimeline model
✓ Create API endpoint for arbitrary date queries
✓ Add interactive Plotly timeline plot
✓ Add "Calculate on Date" form widget

HARD (1-2 days):
✓ Full "What If" scenario system
✓ Batch timeline exports (CSV/Excel/PDF)
✓ Advanced filtering and isotope selection
✓ Multi-sample comparison plots
    """)

    print("\n" + "="*100)
    print("\nLet me know your preferences and I'll implement the features you need!")
    print("="*100 + "\n")


if __name__ == '__main__':
    main()
