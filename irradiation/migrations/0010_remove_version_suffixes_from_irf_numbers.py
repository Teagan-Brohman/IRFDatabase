# Generated manually to clean up IRF numbers with version suffixes

from django.db import migrations
import re


def remove_version_suffixes(apps, schema_editor):
    """
    Remove version suffixes from IRF numbers
    Convert "24-001-v2" -> "24-001", "95-5-v3" -> "95-5", etc.
    This fixes data created with old buggy amendment logic
    """
    IrradiationRequestForm = apps.get_model('irradiation', 'IrradiationRequestForm')

    # Pattern to match version suffixes like -v2, -v3, etc.
    version_suffix_pattern = re.compile(r'-v\d+$')

    updated_count = 0
    for irf in IrradiationRequestForm.objects.all():
        if version_suffix_pattern.search(irf.irf_number):
            # Remove the version suffix
            old_number = irf.irf_number
            new_number = version_suffix_pattern.sub('', irf.irf_number)

            print(f"  Fixing IRF: {old_number} -> {new_number}")
            irf.irf_number = new_number
            irf.save(update_fields=['irf_number'])
            updated_count += 1

    if updated_count > 0:
        print(f"Updated {updated_count} IRF(s) to remove version suffixes")
    else:
        print("No IRF numbers needed fixing (no version suffixes found)")


def add_version_suffixes_back(apps, schema_editor):
    """
    Reverse migration - adds version suffixes back
    (Not recommended, only here for completeness)
    """
    IrradiationRequestForm = apps.get_model('irradiation', 'IrradiationRequestForm')

    for irf in IrradiationRequestForm.objects.filter(version_number__gt=1):
        if not irf.irf_number.endswith(f'-v{irf.version_number}'):
            old_number = irf.irf_number
            new_number = f"{irf.irf_number}-v{irf.version_number}"
            print(f"  Reverting IRF: {old_number} -> {new_number}")
            irf.irf_number = new_number
            irf.save(update_fields=['irf_number'])


class Migration(migrations.Migration):

    dependencies = [
        ("irradiation", "0009_fix_location_naming"),
    ]

    operations = [
        migrations.RunPython(remove_version_suffixes, add_version_suffixes_back),
    ]
