#!/usr/bin/env python3
"""
Simple test to check PyNE gamma energy retrieval for Au-198
"""

try:
    from pyne import data as pyne_data, nucname
    HAS_PYNE = True
except ImportError:
    HAS_PYNE = False
    print("PyNE not available")
    exit(1)

def test_au198_gamma_energy():
    """Test gamma energy retrieval for Au-198"""

    isotope = 'Au-198'
    print(f"Testing gamma energy lookup for {isotope}")
    print("=" * 60)

    # Convert isotope name to PyNE nucid
    nuc_id = nucname.id(isotope)
    print(f"PyNE nucid: {nuc_id}")

    # Try to get gamma energies and intensities
    try:
        intensities = pyne_data.gamma_photon_intensity(nuc_id)
        energies = pyne_data.gamma_energy(nuc_id)

        print(f"\nIntensities type: {type(intensities)}")
        print(f"Intensities: {intensities}")
        print(f"\nEnergies type: {type(energies)}")
        print(f"Energies: {energies}")

        if intensities and energies:
            print(f"\nLength of intensities: {len(intensities)}")
            print(f"Length of energies: {len(energies)}")

            if len(intensities) > 0:
                print(f"\nFirst intensity: {intensities[0]}")
                print(f"Type of first intensity: {type(intensities[0])}")

            if len(energies) > 0:
                print(f"\nFirst energy: {energies[0]}")
                print(f"Type of first energy: {type(energies[0])}")

            # Try to calculate weighted average
            try:
                total_intensity = sum(inten[0] for inten in intensities)
                print(f"\nTotal intensity (sum of inten[0]): {total_intensity}")

                if total_intensity > 0 and len(intensities) == len(energies):
                    weighted_energy_kev = sum(energies[i][0] * intensities[i][0]
                                             for i in range(len(energies))) / total_intensity
                    weighted_energy_mev = weighted_energy_kev / 1000.0
                    print(f"Weighted average energy: {weighted_energy_mev:.3f} MeV")
                else:
                    print(f"Cannot calculate weighted average (len mismatch or zero intensity)")
            except Exception as e:
                print(f"\nError calculating weighted average: {e}")
                import traceback
                traceback.print_exc()

                # Try alternative interpretation
                print("\nTrying alternative: maybe it's a simple list?")
                try:
                    total_intensity = sum(intensities)
                    print(f"Total intensity (direct sum): {total_intensity}")
                    if total_intensity > 0:
                        weighted_energy_kev = sum(energies[i] * intensities[i]
                                                 for i in range(len(energies))) / total_intensity
                        weighted_energy_mev = weighted_energy_kev / 1000.0
                        print(f"Weighted average energy: {weighted_energy_mev:.3f} MeV")
                except Exception as e2:
                    print(f"Also failed: {e2}")

    except (AttributeError, KeyError) as e:
        print(f"Method not available: {e}")

        # Try ecorr fallback
        print("\nTrying ecorr fallback...")
        try:
            ecorr = pyne_data.ecorr(nuc_id)
            print(f"ecorr: {ecorr} MeV")
        except Exception as e2:
            print(f"ecorr also failed: {e2}")

    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_au198_gamma_energy()
