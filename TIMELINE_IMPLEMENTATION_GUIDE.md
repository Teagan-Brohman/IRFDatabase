# Activation Timeline Implementation Guide

## Overview

This guide documents the implementation of enhanced activation timeline tracking for the IRF Database. This feature enables tracking of activity at each step of the irradiation process, decay to current date, and visualization of decay curves.

## What's Been Completed

### 1. Database Model ✅
**File**: `irradiation/models.py`
**Model**: `ActivationTimeline`

The model stores intermediate states during activation calculations:
- `step_number`: Sequential step (0=initial, 1=after first irradiation, etc.)
- `step_type`: initial | irradiation | decay | current
- `step_datetime`: Timestamp for this step
- `inventory`: JSON of isotopic inventory (atoms)
- `total_activity_bq`: Total activity at this step
- `dominant_isotopes`: Top isotopes by activity
- `estimated_dose_rate_1ft`: Dose rate estimate
- `irradiation_log`: Link to specific irradiation (if applicable)
- `decay_time_seconds`: Time elapsed for decay steps

Helper methods:
- `get_activity_mci()`: Convert to mCi
- `get_activity_ci()`: Convert to Ci
- `get_decay_time_display()`: Format decay time (e.g., "5 days, 3 hours")

### 2. Database Migration ✅
**File**: `irradiation/migrations/0013_activation_timeline.py`

Migration created manually (Django not available in current environment).

**To apply migration**:
```bash
python manage.py migrate irradiation
```

## What Needs to Be Implemented

### 3. Modify ActivationCalculator (HIGH PRIORITY)
**File**: `irradiation/activation.py`
**Method**: `calculate_activation()`

**Changes needed**:

```python
def calculate_activation(self, sample, irradiation_logs, flux_configs,
                        min_activity_fraction=0.001, use_cache=True,
                        track_timeline=True):  # NEW PARAMETER
    """
    ...existing docstring...

    Args:
        track_timeline: If True, save intermediate states to database (default: True)
    """

    # ... existing code ...

    # NEW: Initialize timeline tracking
    timeline = [] if track_timeline else None
    step_number = 0

    # NEW: Save initial state
    if track_timeline:
        timeline.append({
            'step_number': step_number,
            'step_type': 'initial',
            'step_datetime': irradiation_logs[0].irradiation_date - timedelta(days=1),
            'description': 'Initial state (before irradiation)',
            'inventory': inventory.copy(),
            'irradiation_log': None,
            'decay_time_seconds': None
        })
        step_number += 1

    # Process each irradiation
    for log in irradiation_logs:
        # ... existing flux config lookup ...

        # NEW: Track decay period if there was a previous irradiation
        if previous_time and track_timeline:
            irr_start = datetime.combine(log.irradiation_date, log.time_in)
            decay_time_s = (irr_start - previous_time).total_seconds()

            if decay_time_s > 0:
                # Decay inventory (existing code already does this)
                # ... existing decay code ...

                # Save decay state to timeline
                timeline.append({
                    'step_number': step_number,
                    'step_type': 'decay',
                    'step_datetime': irr_start - timedelta(seconds=1),
                    'description': f'After {decay_time_s/86400:.1f} day decay period',
                    'inventory': inventory.copy(),
                    'irradiation_log': None,
                    'decay_time_seconds': decay_time_s
                })
                step_number += 1

        # Calculate inventory after this irradiation (existing code)
        inventory, reference_time = self._process_irradiation(
            inventory, log, flux_config, previous_time
        )

        # NEW: Save post-irradiation state to timeline
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

    # NEW: Decay to current date
    current_date = datetime.now()
    if track_timeline and reference_time and current_date > reference_time:
        decay_to_current_s = (current_date - reference_time).total_seconds()

        # Decay inventory to current date
        current_inventory = self._decay_inventory(inventory.copy(), decay_to_current_s)

        # Save current state
        timeline.append({
            'step_number': step_number,
            'step_type': 'current',
            'step_datetime': current_date,
            'description': f'Current date ({decay_to_current_s/86400:.0f} days after last irradiation)',
            'inventory': current_inventory,
            'irradiation_log': None,
            'decay_time_seconds': decay_to_current_s
        })

    # ... existing activity calculation code ...

    # NEW: Return timeline data
    results['timeline'] = timeline if track_timeline else None

    return results
```

### 4. Save Timeline to Database
**File**: `irradiation/activation.py`
**New Method**: `_save_timeline_to_db()`

```python
def _save_timeline_to_db(self, activation_result, timeline):
    """
    Save timeline entries to database

    Args:
        activation_result: ActivationResult instance
        timeline: List of timeline dictionaries
    """
    from .models import ActivationTimeline

    # Clear existing timeline for this result
    ActivationTimeline.objects.filter(activation_result=activation_result).delete()

    # Create timeline entries
    for entry in timeline:
        # Calculate activities for this inventory
        activities = self._calculate_activities(
            entry['inventory'],
            entry['step_datetime'],
            min_activity_fraction=0.001
        )

        total_activity = sum(iso['activity_bq'] for iso in activities['isotopes'].values())

        # Get top 5 isotopes
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
            total_activity_bq=total_activity,
            dominant_isotopes=dominant,
            estimated_dose_rate_1ft=dose_rate,
            irradiation_log=entry.get('irradiation_log'),
            decay_time_seconds=entry.get('decay_time_seconds')
        )

    logger.info(f"Saved {len(timeline)} timeline entries for {activation_result}")
```

**Call this method** after saving ActivationResult:

```python
# In irradiation/views.py calculate_sample_isotopics view:

# After creating/updating ActivationResult
if results.get('timeline'):
    calc._save_timeline_to_db(activation_result, results['timeline'])
```

### 5. Decay to Arbitrary Date Method
**File**: `irradiation/activation.py`
**New Method**: `decay_inventory_to_date()`

```python
def decay_inventory_to_date(self, sample, target_date, irradiation_logs=None, flux_configs=None):
    """
    Calculate isotopic inventory and activity at an arbitrary future date

    Args:
        sample: Sample instance
        target_date: datetime object for target date
        irradiation_logs: Optional QuerySet (will fetch if not provided)
        flux_configs: Optional dict (will fetch if not provided)

    Returns:
        dict with inventory, activities, and metadata at target date
    """
    # Get final inventory at end of last irradiation
    if not irradiation_logs:
        irradiation_logs = sample.irradiation_logs.all().order_by('irradiation_date', 'time_in')

    if not flux_configs:
        from .models import FluxConfiguration
        flux_configs = {fc.location: fc for fc in FluxConfiguration.objects.all()}

    # Calculate final state (use existing method)
    results = self.calculate_activation(
        sample, irradiation_logs, flux_configs,
        use_cache=True, track_timeline=False
    )

    if not results['calculation_successful']:
        return results

    # Get reference time (end of last irradiation)
    reference_time = datetime.fromisoformat(results['reference_time'])

    # If target date is before reference time, cannot calculate
    if target_date < reference_time:
        return {
            'calculation_successful': False,
            'error_message': f'Target date {target_date} is before last irradiation {reference_time}',
            'isotopes': {},
            'total_activity_bq': 0.0
        }

    # Calculate decay time
    decay_time_s = (target_date - reference_time).total_seconds()

    # Get inventory from cached result
    # Need to reconstruct inventory from isotopes
    inventory = {}
    for isotope, data in results['isotopes'].items():
        # Back-calculate atoms from activity: N = A / λ
        half_life_s = data['half_life_s']
        if half_life_s != 'stable' and half_life_s > 0:
            lambda_decay = LAMBDA_LN2 / half_life_s
            inventory[isotope] = data['activity_bq'] / lambda_decay

    # Decay to target date
    decayed_inventory = self._decay_inventory(inventory, decay_time_s)

    # Calculate activities at target date
    target_results = self._calculate_activities(
        decayed_inventory,
        target_date,
        min_activity_fraction=0.001
    )

    target_results['calculation_successful'] = True
    target_results['reference_time'] = target_date.isoformat()
    target_results['decay_time_seconds'] = decay_time_s
    target_results['decay_time_display'] = f"{decay_time_s/86400:.1f} days from last irradiation"
    target_results['total_activity_bq'] = sum(iso['activity_bq'] for iso in target_results['isotopes'].values())
    target_results['estimated_dose_rate_1ft'] = self._estimate_dose_rate(target_results['isotopes'])

    return target_results
```

### 6. API Endpoints
**File**: `irradiation/urls.py`

Add new URL patterns:

```python
# Activation timeline endpoints
path('api/sample/<int:pk>/timeline/', views.sample_timeline_api, name='sample_timeline_api'),
path('api/sample/<int:pk>/activity-at/', views.sample_activity_at_date_api, name='sample_activity_at_date_api'),
```

**File**: `irradiation/views.py`

```python
@require_http_methods(["GET"])
def sample_timeline_api(request, pk):
    """
    API endpoint to get activation timeline for a sample

    Returns JSON array of timeline entries
    """
    sample = get_object_or_404(Sample, pk=pk)

    # Get most recent activation result
    activation_result = sample.activation_results.filter(
        calculation_successful=True
    ).order_by('-calculated_at').first()

    if not activation_result:
        return JsonResponse({'error': 'No activation results found'}, status=404)

    # Get timeline entries
    timeline_entries = activation_result.timeline_entries.all().order_by('step_number')

    timeline_data = []
    for entry in timeline_entries:
        timeline_data.append({
            'step_number': entry.step_number,
            'step_type': entry.step_type,
            'datetime': entry.step_datetime.isoformat(),
            'description': entry.description,
            'activity_bq': float(entry.total_activity_bq),
            'activity_mci': entry.get_activity_mci(),
            'activity_ci': entry.get_activity_ci(),
            'dose_rate_1ft': float(entry.estimated_dose_rate_1ft) if entry.estimated_dose_rate_1ft else None,
            'dominant_isotopes': entry.dominant_isotopes,
            'decay_time': entry.get_decay_time_display(),
            'irradiation_log_id': entry.irradiation_log_id
        })

    return JsonResponse({
        'sample_id': sample.sample_id,
        'timeline': timeline_data,
        'reference_time': activation_result.reference_time.isoformat()
    })


@require_http_methods(["GET"])
def sample_activity_at_date_api(request, pk):
    """
    API endpoint to calculate activity at specific date

    Query params:
        date: ISO format date (e.g., 2025-12-31 or 2025-12-31T15:30:00)
        use_multigroup: true/false (default: true)
    """
    sample = get_object_or_404(Sample, pk=pk)

    # Parse target date
    date_str = request.GET.get('date')
    if not date_str:
        return JsonResponse({'error': 'date parameter required'}, status=400)

    try:
        # Try parsing as datetime first, fall back to date
        try:
            target_date = datetime.fromisoformat(date_str)
        except ValueError:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)'}, status=400)

    use_multigroup = request.GET.get('use_multigroup', 'true').lower() == 'true'

    # Get irradiation logs and flux configs
    irradiation_logs = sample.irradiation_logs.all().order_by('irradiation_date', 'time_in')
    flux_configs = {fc.location: fc for fc in FluxConfiguration.objects.all()}

    # Calculate
    calc = ActivationCalculator(use_multigroup=use_multigroup)
    results = calc.decay_inventory_to_date(sample, target_date, irradiation_logs, flux_configs)

    if not results['calculation_successful']:
        return JsonResponse({
            'error': results.get('error_message', 'Calculation failed')
        }, status=400)

    # Format response
    isotopes_data = {}
    for isotope, data in results['isotopes'].items():
        isotopes_data[isotope] = {
            'activity_bq': data['activity_bq'],
            'activity_mci': data['activity_ci'] * 1000,
            'activity_ci': data['activity_ci'],
            'half_life': data['half_life_display'],
            'fraction': data['fraction']
        }

    return JsonResponse({
        'sample_id': sample.sample_id,
        'target_date': target_date.isoformat(),
        'decay_time': results['decay_time_display'],
        'total_activity_bq': results['total_activity_bq'],
        'total_activity_mci': results['total_activity_bq'] / 3.7e10 * 1000,
        'total_activity_ci': results['total_activity_bq'] / 3.7e10,
        'dose_rate_1ft_mrem_hr': float(results['estimated_dose_rate_1ft']),
        'isotopes': isotopes_data,
        'isotope_count': len(isotopes_data)
    })
```

### 7. Template Updates
**File**: `irradiation/templates/irradiation/sample_detail.html`

Add new tab:

```html
<!-- In tab navigation -->
<li class="nav-item">
    <a class="nav-link" id="timeline-tab" data-bs-toggle="tab" href="#timeline" role="tab">
        Timeline
    </a>
</li>

<!-- In tab content -->
<div class="tab-pane fade" id="timeline" role="tabpanel">
    <h3>Activation Timeline</h3>

    <!-- Timeline Table -->
    <div id="timeline-table-container">
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>Step</th>
                    <th>Date/Time</th>
                    <th>Type</th>
                    <th>Description</th>
                    <th>Activity</th>
                    <th>Dose Rate (1 ft)</th>
                </tr>
            </thead>
            <tbody id="timeline-table-body">
                <!-- Populated by JavaScript -->
            </tbody>
        </table>
    </div>

    <!-- Decay Curve Plot -->
    <div id="decay-curve" style="height: 500px; margin-top: 30px;"></div>

    <!-- Calculate on Date Widget -->
    <div class="card mt-4">
        <div class="card-header">
            <h5>Calculate Activity on Specific Date</h5>
        </div>
        <div class="card-body">
            <div class="row">
                <div class="col-md-6">
                    <label for="target-date">Target Date:</label>
                    <input type="datetime-local" id="target-date" class="form-control">
                </div>
                <div class="col-md-6">
                    <label>&nbsp;</label><br>
                    <button id="calculate-at-date-btn" class="btn btn-primary">Calculate</button>
                </div>
            </div>
            <div id="date-calc-results" class="mt-3" style="display: none;">
                <!-- Results populated by JavaScript -->
            </div>
        </div>
    </div>
</div>

<!-- JavaScript -->
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<script>
// Load timeline data
function loadTimeline() {
    fetch(`/api/sample/{{ sample.pk }}/timeline/`)
        .then(response => response.json())
        .then(data => {
            renderTimelineTable(data.timeline);
            renderDecayCurve(data.timeline);
        });
}

function renderTimelineTable(timeline) {
    const tbody = document.getElementById('timeline-table-body');
    tbody.innerHTML = '';

    timeline.forEach(entry => {
        const row = tbody.insertRow();
        row.innerHTML = `
            <td>${entry.step_number}</td>
            <td>${new Date(entry.datetime).toLocaleString()}</td>
            <td><span class="badge bg-${getStepTypeBadgeClass(entry.step_type)}">${entry.step_type}</span></td>
            <td>${entry.description}</td>
            <td>${entry.activity_mci.toFixed(3)} mCi</td>
            <td>${entry.dose_rate_1ft ? entry.dose_rate_1ft.toFixed(2) + ' mrem/hr' : 'N/A'}</td>
        `;
    });
}

function getStepTypeBadgeClass(stepType) {
    const classes = {
        'initial': 'secondary',
        'irradiation': 'danger',
        'decay': 'info',
        'current': 'success'
    };
    return classes[stepType] || 'secondary';
}

function renderDecayCurve(timeline) {
    // Extract data for plotting
    const dates = timeline.map(e => new Date(e.datetime));
    const activities = timeline.map(e => e.activity_mci);

    const trace = {
        x: dates,
        y: activities,
        mode: 'lines+markers',
        name: 'Activity',
        line: {color: 'rgb(55, 128, 191)', width: 2},
        marker: {size: 8}
    };

    // Mark irradiations
    const irradiations = timeline.filter(e => e.step_type === 'irradiation');
    const irrDates = irradiations.map(e => new Date(e.datetime));
    const irrActivities = irradiations.map(e => e.activity_mci);

    const irrTrace = {
        x: irrDates,
        y: irrActivities,
        mode: 'markers',
        name: 'Irradiations',
        marker: {size: 12, color: 'red', symbol: 'star'}
    };

    // Mark current date
    const current = timeline.find(e => e.step_type === 'current');
    const currentTrace = current ? {
        x: [new Date(current.datetime)],
        y: [current.activity_mci],
        mode: 'markers',
        name: 'Current Date',
        marker: {size: 14, color: 'green', symbol: 'diamond'}
    } : null;

    const plotData = currentTrace ? [trace, irrTrace, currentTrace] : [trace, irrTrace];

    const layout = {
        title: 'Activity Timeline',
        xaxis: {title: 'Date'},
        yaxis: {title: 'Activity (mCi)', type: 'log'},
        hovermode: 'closest'
    };

    Plotly.newPlot('decay-curve', plotData, layout);
}

// Calculate at date functionality
document.getElementById('calculate-at-date-btn').addEventListener('click', function() {
    const targetDate = document.getElementById('target-date').value;
    if (!targetDate) {
        alert('Please select a target date');
        return;
    }

    fetch(`/api/sample/{{ sample.pk }}/activity-at/?date=${targetDate}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
                return;
            }

            const resultsDiv = document.getElementById('date-calc-results');
            resultsDiv.style.display = 'block';
            resultsDiv.innerHTML = `
                <h6>Results for ${new Date(data.target_date).toLocaleString()}</h6>
                <p><strong>Decay Time:</strong> ${data.decay_time}</p>
                <p><strong>Total Activity:</strong> ${data.total_activity_mci.toFixed(3)} mCi (${data.total_activity_ci.toExponential(2)} Ci)</p>
                <p><strong>Dose Rate:</strong> ${data.dose_rate_1ft_mrem_hr.toFixed(2)} mrem/hr at 1 foot</p>
                <p><strong>Number of Isotopes:</strong> ${data.isotope_count}</p>

                <h6>Top Isotopes:</h6>
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Isotope</th>
                            <th>Activity (mCi)</th>
                            <th>Half-Life</th>
                            <th>Fraction</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${Object.entries(data.isotopes)
                            .sort((a, b) => b[1].activity_mci - a[1].activity_mci)
                            .slice(0, 10)
                            .map(([isotope, isoData]) => `
                                <tr>
                                    <td>${isotope}</td>
                                    <td>${isoData.activity_mci.toFixed(3)}</td>
                                    <td>${isoData.half_life}</td>
                                    <td>${(isoData.fraction * 100).toFixed(2)}%</td>
                                </tr>
                            `).join('')}
                    </tbody>
                </table>
            `;
        });
});

// Load timeline on page load
document.addEventListener('DOMContentLoaded', loadTimeline);
</script>
```

### 8. Admin Registration
**File**: `irradiation/admin.py`

```python
from .models import ActivationTimeline

@admin.register(ActivationTimeline)
class ActivationTimelineAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'step_type', 'step_datetime', 'total_activity_bq', 'estimated_dose_rate_1ft']
    list_filter = ['step_type', 'activation_result__sample']
    readonly_fields = ['activation_result', 'step_number', 'step_datetime', 'inventory', 'dominant_isotopes']

    fieldsets = [
        ('Step Information', {
            'fields': ['activation_result', 'step_number', 'step_type', 'step_datetime', 'description']
        }),
        ('Activity Data', {
            'fields': ['total_activity_bq', 'estimated_dose_rate_1ft', 'dominant_isotopes']
        }),
        ('Details', {
            'fields': ['inventory', 'irradiation_log', 'decay_time_seconds'],
            'classes': ['collapse']
        })
    ]
```

## Testing Checklist

- [ ] Run migration: `python manage.py migrate`
- [ ] Calculate activation for a sample with multiple irradiations
- [ ] Verify timeline entries are created
- [ ] Check timeline table displays correctly
- [ ] Verify decay curve renders
- [ ] Test "Calculate on Date" widget with future date
- [ ] Test "Calculate on Date" with past date (should error)
- [ ] Verify activities decay correctly over time
- [ ] Check that current date entry is created
- [ ] Verify dose rates are calculated
- [ ] Test with sample that has no irradiations (should handle gracefully)

## Known Limitations

1. **Computation Time**: Calculating activities for each timeline step adds overhead. Consider:
   - Making timeline tracking optional (`track_timeline=False` parameter)
   - Caching timeline along with ActivationResult

2. **Storage Space**: Timeline can grow large for samples with many irradiations
   - 10 irradiations = ~21 timeline entries (initial + 10×[irradiation+decay] + current)
   - Consider data retention policy

3. **Decay Chain Complexity**: For complex decay chains, intermediate inventory may be incomplete
   - Current implementation focuses on dominant isotopes
   - Very long-lived daughters might be missed in intermediate steps

## Future Enhancements

1. **Export Timeline**: CSV/Excel export of complete timeline
2. **Comparison View**: Compare timelines of multiple samples side-by-side
3. **What-If Scenarios**: "What if I irradiate again on [date]?"
4. **Automated Alerts**: Email when activity drops below threshold
5. **Decay Projections**: Show projected activity for next 30/60/90 days
6. **Isotope Filtering**: Filter timeline by specific isotopes
7. **Zoom Controls**: Interactive zoom on decay curve for specific time periods

## Support

For questions or issues, contact the development team or file an issue in the repository.
