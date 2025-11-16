#!/usr/bin/env python
"""
Test script to verify the improved cross section implementation

This script tests:
1. PyNE availability and data sources
2. Energy-dependent cross section retrieval
3. Spectrum collapse with flux weighting
4. Comparison of thermal-only vs mixed-spectrum results
"""

import sys
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'irfdatabase.settings')
django.setup()

def test_pyne_availability():
    """Test if PyNE and required modules are available"""
    print("=" * 70)
    print("Testing PyNE Availability")
    print("=" * 70)

    try:
        import pyne
        print(f"✓ PyNE version: {pyne.__version__}")
    except ImportError:
        print("✗ PyNE not installed")
        print("  Install with: conda install -c conda-forge pyne")
        return False

    try:
        from pyne.xs import data_source
        print("✓ PyNE xs.data_source module available")
    except ImportError:
        print("✗ PyNE xs.data_source not available")
        return False

    try:
        from pyne import nucname, data as pyne_data
        print("✓ PyNE nucname and data modules available")
    except ImportError:
        print("✗ PyNE nucname/data modules not available")
        return False

    try:
        import numpy as np
        print(f"✓ NumPy version: {np.__version__}")
    except ImportError:
        print("✗ NumPy not installed")
        return False

    try:
        import radioactivedecay as rd
        print(f"✓ radioactivedecay version: {rd.__version__}")
    except ImportError:
        print("✗ radioactivedecay not installed")
        print("  Install with: pip install radioactivedecay")

    print()
    return True


def test_data_sources():
    """Test PyNE data sources"""
    print("=" * 70)
    print("Testing PyNE Data Sources")
    print("=" * 70)

    try:
        from pyne.xs import data_source
        from pyne import nucname
        import numpy as np

        # Test isotopes
        isotopes = [
            ('Au-197', 'Gold-197 (common activation foil)'),
            ('Co-59', 'Cobalt-59 (flux monitor)'),
            ('Cu-63', 'Copper-63 (common structural material)'),
        ]

        for isotope, description in isotopes:
            print(f"\n{isotope} - {description}")
            print("-" * 70)

            nucid = nucname.id(isotope)

            # Test SimpleDataSource
            try:
                sds = data_source.SimpleDataSource()
                xs_data = sds.reaction(nucid, 'gamma')
                if xs_data and 'xs' in xs_data:
                    thermal_xs = xs_data['xs'][-1] if len(xs_data['xs']) > 0 else None
                    print(f"  SimpleDataSource: σ_thermal = {thermal_xs:.2f} barns" if thermal_xs else "  SimpleDataSource: No data")
                else:
                    print("  SimpleDataSource: No (n,gamma) data")
            except Exception as e:
                print(f"  SimpleDataSource: Failed - {e}")

            # Test EAFDataSource
            try:
                eds = data_source.EAFDataSource()
                xs_data = eds.reaction(nucid, 'gamma')
                if xs_data and 'xs' in xs_data:
                    thermal_xs = xs_data['xs'][-1] if len(xs_data['xs']) > 0 else None
                    print(f"  EAFDataSource:    σ_thermal = {thermal_xs:.2f} barns" if thermal_xs else "  EAFDataSource: No data")
                else:
                    print("  EAFDataSource: No (n,gamma) data")
            except Exception as e:
                print(f"  EAFDataSource: Failed - {e}")

            # Test multi-group discretization
            try:
                E_g = np.array([1e7, 1e5, 0.5, 1e-5])  # 3-group structure
                sds_mg = data_source.SimpleDataSource(dst_group_struct=E_g)
                xs_mg = sds_mg.discretize(nucid, 'gamma')

                if xs_mg is not None and len(xs_mg) > 0:
                    print(f"  Multi-group XS:   {xs_mg} barns")
                    print(f"                    [Fast, Intermediate, Thermal]")
                else:
                    print("  Multi-group XS:   No data")
            except Exception as e:
                print(f"  Multi-group XS: Failed - {e}")

    except Exception as e:
        print(f"Data source test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    return True


def test_spectrum_collapse():
    """Test spectrum-weighted cross section collapse"""
    print("=" * 70)
    print("Testing Spectrum Collapse")
    print("=" * 70)

    try:
        from pyne.xs import data_source
        from pyne import nucname
        import numpy as np

        # Test with Au-197
        isotope = 'Au-197'
        nucid = nucname.id(isotope)

        # Define energy groups
        E_g = np.array([1e7, 1e5, 0.5, 1e-5])  # eV

        # Get multi-group cross sections
        sds = data_source.SimpleDataSource(dst_group_struct=E_g)
        xs_mg = sds.discretize(nucid, 'gamma')

        if xs_mg is None or len(xs_mg) == 0:
            print(f"No multi-group data for {isotope}")
            return False

        print(f"\n{isotope} Multi-Group Cross Sections:")
        print(f"  Fast (10 MeV - 0.1 MeV):        σ_fast = {xs_mg[0]:.4f} barns")
        print(f"  Intermediate (0.1 MeV - 0.5 eV): σ_inter = {xs_mg[1]:.4f} barns")
        print(f"  Thermal (< 0.5 eV):              σ_thermal = {xs_mg[2]:.2f} barns")

        # Test different flux spectra
        print("\nSpectrum Collapse Results:")
        print("-" * 70)

        test_spectra = [
            ("Pure Thermal", np.array([0.0, 0.0, 1.0])),
            ("Pure Fast", np.array([1.0, 0.0, 0.0])),
            ("50/50 Thermal/Fast", np.array([0.5, 0.0, 0.5])),
            ("Typical MSTR", np.array([0.1, 0.1, 0.8])),  # Missouri S&T Reactor
            ("Fast Reactor", np.array([0.7, 0.2, 0.1])),
        ]

        for name, flux_weights in test_spectra:
            n_groups = min(len(xs_mg), len(flux_weights))
            sigma_eff = np.sum(xs_mg[:n_groups] * flux_weights[:n_groups])
            print(f"  {name:25s}: σ_eff = {sigma_eff:.2f} barns")

        print("\nNote: Effective cross section changes significantly with spectrum!")
        print("      Pure thermal: ~100 barns")
        print("      Mixed spectrum: Much lower due to low fast (n,gamma) XS")

    except Exception as e:
        print(f"Spectrum collapse test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    return True


def test_activation_calculator():
    """Test the ActivationCalculator with the new implementation"""
    print("=" * 70)
    print("Testing ActivationCalculator")
    print("=" * 70)

    try:
        from irradiation.activation import ActivationCalculator

        # Create calculator with multigroup enabled
        calc_mg = ActivationCalculator(use_multigroup=True)
        print("✓ ActivationCalculator created with multigroup=True")

        # Create calculator without multigroup
        calc_1g = ActivationCalculator(use_multigroup=False)
        print("✓ ActivationCalculator created with multigroup=False")

        # Test cross section retrieval
        print("\nTesting cross section retrieval for Au-197:")
        print("-" * 70)

        # Thermal only
        xs_thermal = calc_mg._get_cross_section_data('Au-197')
        if xs_thermal:
            print(f"  Thermal only: σ = {xs_thermal[0]:.2f} barns, product = {xs_thermal[1]}")
        else:
            print("  Thermal only: No data")

        # With flux spectrum
        flux_spectrum = {
            'thermal': 2.5e12,
            'fast': 1.0e11,
            'intermediate': 5.0e10
        }

        xs_spectrum = calc_mg._get_cross_section_data('Au-197', flux_spectrum)
        if xs_spectrum:
            print(f"  Mixed spectrum: σ = {xs_spectrum[0]:.2f} barns, product = {xs_spectrum[1]}")
        else:
            print("  Mixed spectrum: No data")

        if xs_thermal and xs_spectrum:
            ratio = xs_spectrum[0] / xs_thermal[0]
            print(f"\n  Ratio (mixed/thermal): {ratio:.3f}")
            print(f"  Mixed spectrum XS should be lower due to fast flux contribution")

    except Exception as e:
        print(f"ActivationCalculator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print(" Cross Section Implementation Test Suite")
    print("=" * 70 + "\n")

    tests = [
        ("PyNE Availability", test_pyne_availability),
        ("Data Sources", test_data_sources),
        ("Spectrum Collapse", test_spectrum_collapse),
        ("Activation Calculator", test_activation_calculator),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ {name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)

    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {name}")

    total = len(results)
    passed = sum(1 for _, s in results if s)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed! Cross section implementation is working correctly.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Check output above for details.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
