# Neutron Activation & Dose Rate Test Suite Documentation

## Overview

This test suite validates the neutron activation analysis and dose rate calculations against NIST/NRC reference data and empirical measurements from well-characterized calibration sources.

**Test Coverage:**
- ✓ Dose rate calculations (Co-60, Cs-137, Na-22, Au-198)
- ✓ Gamma energy lookups and multi-gamma emitters
- ✓ Complete gold foil activation scenarios
- ✓ Mass scaling (activity ∝ mass)
- ✓ Flux scaling (activity ∝ flux)
- ✓ Decay time calculations
- ✓ Multi-element samples
- ✓ Saturation behavior
- ✓ Regression tests (prevent K=6 bug)

## Test Suite Structure

```
IRFDatabase/
├── tests/
│   ├── fixtures/
│   │   ├── __init__.py
│   │   └── reference_data.py          # NIST/NRC reference constants
│   ├── test_dose_rate_calculations.py # Unit tests for dose rates
│   └── test_activation_complete.py    # Integration tests for activation
├── test_suite_validation.py           # Standalone validation script
└── docs/
    └── TEST_SUITE_DOCUMENTATION.md    # This file
```

## Running Tests

### Method 1: Django Test Framework (Recommended for CI/CD)

```bash
# Activate environment
conda activate irfdatabase

# Run all tests
python manage.py test

# Run specific test module
python manage.py test tests.test_dose_rate_calculations

# Run specific test class
python manage.py test tests.test_dose_rate_calculations.DoseRateNISTValidationTests

# Run with verbosity
python manage.py test --verbosity=2

# Keep database for debugging
python manage.py test --keepdb
```

### Method 2: Standalone Validation Script

```bash
# Activate environment
conda activate irfdatabase

# Run standalone script
python test_suite_validation.py

# The script will:
# - Run all validation tests
# - Print detailed results
# - Return exit code 0 (pass) or 1 (fail)
```

### Method 3: Direct Python unittest

```bash
# Run individual test file
python -m unittest tests.test_dose_rate_calculations

# Run specific test
python -m unittest tests.test_dose_rate_calculations.DoseRateNISTValidationTests.test_co60_1ci_1ft_dose_rate
```

## Test Categories

### 1. Dose Rate Formula Tests (`test_dose_rate_calculations.py`)

**Purpose**: Validate the dose rate formula against NIST reference data

**Key Tests:**
- `test_dose_rate_constant_is_530()` - Ensures K=530, not 6 (regression)
- `test_co60_1ci_1ft_dose_rate()` - 1 Ci Co-60 @ 1 ft = 1300-1500 mrem/hr
- `test_cs137_1ci_1ft_dose_rate()` - 1 Ci Cs-137 @ 1 ft = ~330 mrem/hr
- `test_na22_1ci_1ft_dose_rate()` - 1 Ci Na-22 @ 1 ft = ~1200 mrem/hr
- `test_au198_1ci_1ft_dose_rate()` - 1 Ci Au-198 @ 1 ft = ~220 mrem/hr

**Reference Formula:**
```
dose_rate (mrem/hr) = K × C (Ci) × E_total (MeV)
where K = 530 (empirically derived)
```

### 2. Gamma Energy Calculation Tests

**Purpose**: Verify gamma energy lookups from PyNE

**Key Tests:**
- `test_co60_gamma_energy()` - Total energy = 2.5 MeV (1.173 + 1.332)
- `test_multi_gamma_emitter_not_averaged()` - Regression test for old bug

**Critical Check**: Multi-gamma emitters must calculate **total** energy per decay, not weighted average.

### 3. Activation Integration Tests (`test_activation_complete.py`)

**Purpose**: Validate complete activation workflow

**Key Scenarios:**
- `test_standard_gold_foil_scenario()` - 2.5g Au, 1hr @ 2.5×10¹² n/cm²/s
  - Expected: 543 mCi at EOI, 251 mCi after 3 days
- `test_gold_foil_mass_scaling()` - Activity scales linearly with mass
- `test_gold_foil_flux_scaling()` - Activity scales linearly with flux
- `test_au198_decay_over_time()` - Exponential decay validation
- `test_multi_element_sample()` - Au-Al alloy produces Au-198 and Al-28

### 4. Decay Time Tests

**Purpose**: Validate radioactive decay calculations

**Test Points:**
- Au-198: 0, 1, 3, 7 days (t½ = 2.69 days)
- Co-60: 1 year decay (t½ = 5.27 years)

**Formula:** `A(t) = A₀ × exp(-λt)` where `λ = ln(2)/t½`

### 5. Saturation Tests

**Purpose**: Verify saturation formula for long irradiations

**Formula:** `N(t) = (R/λ) × [1 - exp(-λt)]`

**Test Points:**
- 1 half-life: 50% saturation
- 3 half-lives: 87.5% saturation
- 7 half-lives: 99.22% saturation

## Reference Data Sources

### NIST/NRC Dose Rate Constants

| Isotope | Gamma Energy (MeV) | Dose Rate @ 1 Ci, 1 ft (mrem/hr) | Source |
|---------|-------------------|----------------------------------|--------|
| Co-60   | 2.504             | 1300-1500                        | NIST RadData, NUREG-1556 |
| Cs-137  | 0.662             | 330                              | NIST RadData, NUREG-1556 |
| Na-22   | 2.29              | 1200                             | Literature, NIST |
| Au-198  | 0.419             | 220                              | Calculated (530×1×0.419) |

### Neutron Activation Cross-Sections

| Target | Product | σ_thermal (barns) | t½ (product) | Source |
|--------|---------|------------------|-------------|--------|
| Au-197 | Au-198  | 98.65            | 2.69 days   | IAEA, ENDF/B-VIII.0 |
| Al-27  | Al-28   | 0.231            | 2.24 min    | IAEA, ENDF/B-VIII.0 |
| Co-59  | Co-60   | 37.18            | 5.27 years  | IAEA, ENDF/B-VIII.0 |
| Mn-55  | Mn-56   | 13.3             | 2.58 hours  | IAEA, ENDF/B-VIII.0 |

## Test Tolerances

| Measurement Type | Tolerance | Reason |
|-----------------|-----------|--------|
| Dose rates      | ±10%      | Literature variation in reference values |
| Activities      | ±5%       | Calculation precision |
| Gamma energies  | ±1%       | PyNE data precision |
| Cross-sections  | ±5%       | Nuclear data uncertainty |

## Expected Test Results

### Passing Criteria

All tests should pass when:
1. Dose rate constant K = 530 (not 6)
2. Gamma energies match PyNE data within ±1%
3. Dose rates match NIST references within ±10%
4. Activities scale linearly with mass and flux
5. Decay follows exponential law
6. Saturation follows production-decay balance

### Known Issues

**PyNE Dependency:**
- Some tests require PyNE for gamma data
- If PyNE unavailable, gamma energy tests will skip
- Fallback to simplified cross-section database

**Database State:**
- Integration tests create/modify database
- Use `--keepdb` to preserve test database for debugging
- Tests are isolated with `TestCase` transactions

## Adding New Test Cases

### 1. Add Reference Data

Edit `tests/fixtures/reference_data.py`:

```python
NIST_DOSE_CONSTANTS['Ir-192'] = {
    'gamma_energy_mev': 0.38,  # Average
    'dose_rate_1ci_1ft_mrem_hr': 480,
    'dose_rate_tolerance_percent': 10,
    'source': 'NIST RadData',
}
```

### 2. Create Unit Test

Add to `tests/test_dose_rate_calculations.py`:

```python
def test_ir192_1ci_1ft_dose_rate(self):
    """Test Ir-192: 1 Ci at 1 foot = ~480 mrem/hr"""
    ref_data = NIST_DOSE_CONSTANTS['Ir-192']
    expected = ref_data['dose_rate_1ci_1ft_mrem_hr']

    isotopes = self._create_isotope_dict('Ir-192', 1.0)
    dose_rate = self.calc._estimate_dose_rate(isotopes)

    delta = expected * 0.10
    self.assertAlmostEqual(dose_rate, expected, delta=delta)
```

### 3. Create Integration Test

Add to `tests/test_activation_complete.py`:

```python
def test_cobalt_wire_activation(self):
    """Test Co-59 wire activation to Co-60"""
    # Create Co wire sample
    # Create irradiation scenario
    # Validate Co-60 production
```

### 4. Update Standalone Script

Add to `test_suite_validation.py`:

```python
# In test_dose_rate_constants():
isotopes_ir192 = {'Ir-192': {'activity_ci': 1.0, 'activity_bq': 3.7e10}}
dose_ir192 = self.calc._estimate_dose_rate(isotopes_ir192)
# ... validation logic
```

## Regression Tests

### Critical Bugs to Prevent

**1. K=6 Bug (FIXED)**
- **Problem**: Dose rate constant was 6 instead of 530
- **Impact**: 88× underestimation
- **Test**: `test_dose_rate_constant_is_530()`
- **Prevention**: Explicit check that K ≠ 6

**2. Weighted Average Bug (FIXED)**
- **Problem**: Divided by total_intensity instead of 100
- **Impact**: 2× error for multi-gamma emitters (Co-60)
- **Test**: `test_multi_gamma_emitter_not_averaged()`
- **Prevention**: Check Co-60 energy > 2.0 MeV (not ~1.25 MeV)

## Troubleshooting

### Test Failures

**Symptom**: Co-60 dose rate test fails
```
AssertionError: 1327 != 1400 within delta 140
```

**Possible Causes:**
1. PyNE not installed → gamma energy incorrect
2. K constant changed → check activation.py line 1459
3. Gamma energy calculation bug returned → check line 1384

**Solution:**
```bash
# Verify PyNE installation
python -c "from pyne import data; print('PyNE OK')"

# Check K constant
grep "K = " irradiation/activation.py | grep -v "#"

# Run standalone test for detailed output
python test_suite_validation.py
```

**Symptom**: ImportError for tests.fixtures

**Solution:**
```bash
# Ensure __init__.py files exist
touch tests/__init__.py
touch tests/fixtures/__init__.py

# Add project to PYTHONPATH
export PYTHONPATH=/path/to/IRFDatabase:$PYTHONPATH
```

**Symptom**: Database errors in integration tests

**Solution:**
```bash
# Run migrations
python manage.py migrate

# Clear test database
python manage.py test --keepdb=False
```

### Performance

**Expected Runtime:**
- Unit tests: ~5-10 seconds
- Integration tests: ~15-30 seconds
- Standalone script: ~2-5 seconds
- Full suite: ~30-45 seconds

**Slow Tests:**
- If tests take > 1 minute, check:
  - Database transaction overhead
  - PyNE data loading (first time)
  - Network issues (if fetching external data)

## Continuous Integration

### GitHub Actions Example

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Conda
      uses: conda-incubator/setup-miniconda@v2
      with:
        environment-file: environment.yml
        activate-environment: irfdatabase

    - name: Run tests
      run: |
        conda activate irfdatabase
        python manage.py test --verbosity=2
        python test_suite_validation.py
```

## References

### Standards & Guidelines
- **NIST RadData**: https://www.nist.gov/pml/radiation-physics
- **NRC NUREG-1556**: Consolidated Guidance About Materials Licenses
- **IAEA Safety Reports**: Radiation Protection guidance
- **ANSI/ANS-6.1.1**: Neutron and Gamma-Ray Fluence-to-Dose Factors

### Nuclear Data Libraries
- **ENDF/B-VIII.0**: https://www.nndc.bnl.gov/endf/
- **PyNE Documentation**: https://pyne.io/
- **IAEA Nuclear Data Services**: https://www-nds.iaea.org/

### Health Physics References
- Cember & Johnson, "Introduction to Health Physics", 5th Ed.
- Knoll, "Radiation Detection and Measurement", 4th Ed.
- Turner, "Atoms, Radiation, and Radiation Protection", 3rd Ed.

## Version History

- **v1.0** (2025-11-17): Initial test suite creation
  - 25+ test cases covering dose rates, activation, decay
  - NIST/NRC reference data validation
  - Regression tests for K=6 and gamma energy bugs
  - Standalone validation script
  - Django test integration

## Contact & Support

For questions about the test suite:
1. Check this documentation
2. Review test source code comments
3. Run standalone script for detailed output
4. Consult DOSE_RATE_FIX_SUMMARY.md for bug history

---

**Last Updated**: 2025-11-17
**Maintainer**: IRF Database Development Team
**Status**: Active, all tests passing ✓
