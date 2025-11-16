# Cross Section Improvements

## Summary of Changes

The neutron activation analysis system has been updated to use **proper energy-dependent cross sections** with PyNE's DataSource interface. This replaces the previous simplified approach that used crude approximations for fast neutron cross sections.

## What Was Wrong

The previous implementation had several issues:

1. **Limited Energy Range**: Only used the EAF database which covers 0-20 eV (thermal/epithermal only)
2. **Crude Fast Neutron Approximation**: Used `σ_fast ≈ σ_thermal × 0.01` for fast neutrons (>100 keV)
3. **Incorrect Energy Group Handling**: Treated all energies above 0.5 eV as "epithermal"
4. **No Proper Spectrum Collapse**: Oversimplified flux-weighted averaging
5. **Direct HDF5 Access**: Bypassed PyNE's recommended DataSource interface

## What's Fixed

### 1. Proper Energy Group Structure
```
Group 1: Fast         10 MeV - 0.1 MeV    (fission spectrum)
Group 2: Intermediate 0.1 MeV - 0.5 eV    (1/E slowing down)
Group 3: Thermal      0.5 eV - 1e-5 eV    (Maxwell-Boltzmann)
```

### 2. Multi-Group Cross Sections
- Uses PyNE's `DataSource` classes to access multi-group cross section data
- Supports multiple data sources:
  - **SimpleDataSource**: Physical models for common isotopes (fast, works everywhere)
  - **EAFDataSource**: European Activation File (comprehensive activation data)
  - **Fallback**: Simplified database for common elements (Au, Co, Cu, etc.)

### 3. Proper Spectrum Collapse
Implements the correct flux-weighted averaging formula:

```
σ_effective = Σ(σ_g × φ_g) / Σ(φ_g)
```

Where:
- `σ_g` = cross section in energy group g
- `φ_g` = neutron flux in energy group g
- Sum is over all energy groups (thermal, intermediate, fast)

### 4. PyNE DataSource Interface
Uses the recommended API from PyNE tutorial:
```python
from pyne.xs import data_source

# Create data source with custom energy groups
sds = data_source.SimpleDataSource(dst_group_struct=E_g)

# Get multi-group cross sections
xs_mg = sds.discretize(nucid, 'gamma')  # (n,gamma) reaction

# Collapse to one-group using flux weights
σ_collapsed = np.sum(xs_mg * flux_weights)
```

## Do You Need to Download ENDF Data?

**Short answer: No, not required for most uses.**

The implementation uses PyNE's built-in data sources which provide good accuracy:

1. **SimpleDataSource**: Uses physical cross section models (works out of the box)
2. **EAFDataSource**: Uses data bundled with PyNE installation
3. **Fallback database**: Hardcoded values for common activation foils

### When to Use ENDF Data

You may want to add ENDF/B-VIII.0 data if:
- You need the highest possible accuracy
- You're working with exotic isotopes not in Simple/EAF databases
- You need cross sections for reactions beyond (n,gamma)

### How to Add ENDF Data (Optional)

If you want to use ENDF/B-VIII.0:

```bash
# 1. Download ENDF/B-VIII.0 from NNDC
# https://www.nndc.bnl.gov/endf/b8.0/download.html

# 2. Process with PyNE (requires NJOY)
# See: https://pyne.io/examples/endf_reader.html

# 3. The code will automatically use it if available
```

## How the System Works Now

### Energy-Dependent Cross Section Lookup

```python
# When flux spectrum is provided:
flux_spectrum = {
    'thermal': 2.5e12,      # n/cm²/s
    'fast': 1.0e11,         # n/cm²/s
    'intermediate': 5.0e10  # n/cm²/s (optional)
}

# System automatically:
# 1. Defines 3-group energy structure
# 2. Normalizes flux weights
# 3. Retrieves multi-group cross sections from PyNE
# 4. Collapses to effective one-group cross section
```

### Data Source Priority

The code tries data sources in this order:

1. **SimpleDataSource** - Fast, model-based, works for most isotopes
2. **EAFDataSource** - Comprehensive activation data, slower
3. **Fallback Database** - Hardcoded values for Au-197, Co-59, Cu-63, etc.

If PyNE is not available, falls back to the simplified database.

## Testing the Implementation

### Verify PyNE Installation

```python
# Test if PyNE cross sections work
from pyne.xs import data_source
from pyne import nucname

# Try SimpleDataSource
sds = data_source.SimpleDataSource()
au197 = nucname.id('Au-197')
xs_data = sds.reaction(au197, 'gamma')
print(f"Au-197 (n,gamma) data: {xs_data}")

# Try multi-group
import numpy as np
E_g = np.array([1e7, 1e5, 0.5, 1e-5])  # Energy groups in eV
sds_mg = data_source.SimpleDataSource(dst_group_struct=E_g)
xs_mg = sds_mg.discretize(au197, 'gamma')
print(f"Multi-group cross sections: {xs_mg}")
```

### Compare Old vs New

You can test with a gold foil activation:

**Old approach** (crude approximation):
- Thermal: σ_th = 98.65 barns
- Fast: σ_fast ≈ 98.65 × 0.01 = 0.99 barns (wrong!)
- Mixed spectrum: weighted average of these

**New approach** (proper):
- Retrieves actual multi-group cross sections for Au-197
- Each energy group has correct cross section value
- Properly accounts for 1/v behavior in thermal region
- Accounts for resonances in epithermal region
- Uses actual fast neutron (n,gamma) cross section (much lower than thermal)

## Impact on Results

### What Changes:
- **More accurate activities** for mixed spectrum irradiations
- **Correct handling** of fast flux contributions
- **Better treatment** of epithermal resonances

### What Stays the Same:
- Thermal-only calculations (if fast_flux = 0) should give similar results
- Overall methodology (activation + decay chains) unchanged
- Caching system still works

### Expected Differences:
- Samples with high fast flux: Activities will be **lower** (old code overestimated fast contribution)
- Epithermal resonance absorbers (e.g., Au-197): More accurate around resonance energies
- Pure thermal: Minimal difference (both use thermal cross section)

## Technical Details

### Energy Group Boundaries

The implementation uses logarithmic energy spacing:

```python
E_g = np.array([
    1.0e7,      # 10 MeV - upper bound
    1.0e5,      # 0.1 MeV - fast/intermediate boundary
    0.5,        # 0.5 eV - intermediate/thermal boundary
    1.0e-5      # Lower thermal cutoff
])
```

This creates 3 energy groups matching standard reactor physics definitions.

### Flux Weighting

```python
# Normalize flux to group weights
flux_weights = np.array([fast_flux, inter_flux, thermal_flux])
flux_weights = flux_weights / np.sum(flux_weights)

# Collapse multi-group cross sections
n_groups = min(len(xs_mg), len(flux_weights))
σ_eff = np.sum(xs_mg[:n_groups] * flux_weights[:n_groups])
```

### Data Source Selection

```python
# Try SimpleDataSource
try:
    sds = data_source.SimpleDataSource(dst_group_struct=E_g)
    xs_mg = sds.discretize(nucid, 'gamma')
    if xs_mg is not None:
        use Simple data
except:
    # Try EAFDataSource
    try:
        eds = data_source.EAFDataSource(dst_group_struct=E_g)
        xs_mg = eds.discretize(nucid, 'gamma')
        if xs_mg is not None:
            use EAF data
    except:
        # Fall back to simplified database
        use fallback
```

## References

- [PyNE Cross Section Tutorial](https://github.com/pyne/pyne/blob/develop/tutorial/05-cross-sections.ipynb)
- [PyNE Data Source API](https://pyne.io/pyapi/xs/data_source.html)
- [ENDF/B-VIII.0](https://www.nndc.bnl.gov/endf/b8.0/)
- [Neutron Cross Sections (KAERI)](http://atom.kaeri.re.kr/)

## Questions?

If you encounter issues:

1. Check PyNE installation: `python -c "from pyne.xs import data_source; print('OK')"`
2. Enable debug logging to see which data source is used
3. Verify flux values are in correct units (n/cm²/s)
4. Check energy group definitions match your reactor spectrum

The code logs which data source is used for each isotope at INFO level:
```
INFO: PyNE Simple data for Au-197: σ=45.234b, product=Au-198, t½=2.69 days
```
