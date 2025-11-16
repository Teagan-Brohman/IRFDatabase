#!/usr/bin/env python3
"""
Diagnose issues with timeline API and irradiation logs display
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'irfdb.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from irradiation.models import Sample, SampleIrradiationLog

print("=" * 80)
print("DIAGNOSTIC REPORT")
print("=" * 80)

# Check sample 2
print("\n1. Checking Sample ID 2...")
try:
    sample = Sample.objects.get(pk=2)
    print(f"   ✓ Found sample: {sample.sample_id}")
    print(f"   ✓ Is combo: {sample.is_combo}")

    # Check irradiation logs
    print("\n2. Checking irradiation logs...")
    logs = sample.get_irradiation_logs()
    print(f"   ✓ Total logs found: {logs.count()}")

    if logs.exists():
        print("\n   Irradiation Log Details:")
        for i, log in enumerate(logs, 1):
            print(f"\n   Log #{i}:")
            print(f"      Date: {log.irradiation_date}")
            print(f"      IRF: {log.irf.irf_number}")
            print(f"      Location: {log.actual_location}")
            print(f"      Power: {log.actual_power} kW")
            print(f"      Time: {log.total_time} {log.get_total_time_unit_display()}")
            print(f"      Experimenter: {log.experimenter_name}")

            # Check if fluence method/property exists
            try:
                fluence = log.fluence
                print(f"      Fluence: {fluence} kW-hrs")
            except AttributeError:
                print(f"      ❌ Fluence property/method MISSING")
                print(f"         (This would cause template error)")
    else:
        print("   ℹ No irradiation logs found for this sample")

except Sample.DoesNotExist:
    print("   ❌ Sample with ID 2 not found")

# Check URL routing
print("\n3. Checking URL routing...")
from django.urls import reverse
try:
    url = reverse('irradiation:sample_timeline', kwargs={'pk': 2})
    print(f"   ✓ Timeline URL resolves to: {url}")
except Exception as e:
    print(f"   ❌ Timeline URL resolution failed: {e}")

try:
    url = reverse('irradiation:activity_at_date', kwargs={'pk': 2})
    print(f"   ✓ Activity-at-date URL resolves to: {url}")
except Exception as e:
    print(f"   ❌ Activity-at-date URL resolution failed: {e}")

# Check if views can be imported
print("\n4. Checking views...")
try:
    from irradiation import views
    print(f"   ✓ get_sample_timeline exists: {hasattr(views, 'get_sample_timeline')}")
    print(f"   ✓ calculate_activity_at_date exists: {hasattr(views, 'calculate_activity_at_date')}")
except Exception as e:
    print(f"   ❌ Views import failed: {e}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\nIssues found:")
print("1. Check if SampleIrradiationLog.fluence property exists")
print("2. Check if Django server needs restart to pick up new URLs")
print("3. Verify timeline calculation has been run for this sample")
