#!/usr/bin/env python3
"""
Simple fluence calculation test (no database)
"""

from decimal import Decimal

# Mock the fluence method
def fluence(actual_power, total_time, total_time_unit):
    """
    Calculate total fluence (kW-hrs)
    Fluence = Power × Time
    Converts time to hours based on unit
    """
    power_kw = float(actual_power)
    time = float(total_time)

    # Convert time to hours based on unit
    if total_time_unit == 'hr':
        time_hours = time
    elif total_time_unit == 'min':
        time_hours = time / 60.0
    elif total_time_unit == 'sec':
        time_hours = time / 3600.0
    else:
        # Default to minutes if unknown
        time_hours = time / 60.0

    return power_kw * time_hours

print("=" * 60)
print("FLUENCE CALCULATION TEST")
print("=" * 60)

print(f"\nTesting power: 200 kW")
print(f"\n{'Time':<15} {'Unit':<10} {'Fluence (kW-hrs)':<20} {'Expected':<20} {'Status'}")
print("-" * 80)

test_cases = [
    (4.0, 'hr', 800.0),      # 200 kW × 4 hrs = 800 kW-hrs
    (240.0, 'min', 800.0),   # 200 kW × 4 hrs (240 min) = 800 kW-hrs
    (14400.0, 'sec', 800.0), # 200 kW × 4 hrs (14400 sec) = 800 kW-hrs
    (1.0, 'hr', 200.0),      # 200 kW × 1 hr = 200 kW-hrs
    (30.0, 'min', 100.0),    # 200 kW × 0.5 hrs (30 min) = 100 kW-hrs
    (1800.0, 'sec', 100.0),  # 200 kW × 0.5 hrs (1800 sec) = 100 kW-hrs
]

all_pass = True
for test_time, unit, expected in test_cases:
    # Calculate fluence
    calculated = fluence(Decimal('200.0'), Decimal(str(test_time)), unit)

    # Check if correct
    is_correct = abs(calculated - expected) < 0.01
    status = "✓ PASS" if is_correct else "❌ FAIL"
    if not is_correct:
        all_pass = False

    print(f"{test_time:<15.1f} {unit:<10} {calculated:<20.2f} {expected:<20.2f} {status}")

print("\n" + "=" * 60)
if all_pass:
    print("✓ ALL TESTS PASSED")
else:
    print("❌ SOME TESTS FAILED")
print("=" * 60)
