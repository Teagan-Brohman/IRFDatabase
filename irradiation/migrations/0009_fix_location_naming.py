# Generated manually to fix location naming inconsistencies

from django.db import migrations


def fix_location_names(apps, schema_editor):
    """
    Fix location naming inconsistencies between forms and models
    Convert old form values to match model choices
    """
    IrradiationRequestForm = apps.get_model('irradiation', 'IrradiationRequestForm')
    SampleIrradiationLog = apps.get_model('irradiation', 'SampleIrradiationLog')

    # Mapping from old form values to correct model values
    location_mapping = {
        'bare_rabbit_tube': 'bare_rabbit',
        'cadmium_rabbit_tube': 'cad_rabbit',
        # These don't need changes but include for completeness
        'beam_port': 'beam_port',
        'thermal_column': 'thermal_column',
        'other': 'other',
    }

    # Fix IRF irradiation_location field (comma-separated list)
    for irf in IrradiationRequestForm.objects.all():
        if irf.irradiation_location:
            locations = [loc.strip() for loc in irf.irradiation_location.split(',')]
            fixed_locations = []
            changed = False

            for loc in locations:
                if loc in location_mapping:
                    fixed_loc = location_mapping[loc]
                    if fixed_loc != loc:
                        changed = True
                    fixed_locations.append(fixed_loc)
                else:
                    fixed_locations.append(loc)

            if changed:
                irf.irradiation_location = ', '.join(fixed_locations)
                irf.save(update_fields=['irradiation_location'])

    # Fix SampleIrradiationLog actual_location field
    for log in SampleIrradiationLog.objects.all():
        if log.actual_location and log.actual_location in location_mapping:
            new_location = location_mapping[log.actual_location]
            if new_location != log.actual_location:
                log.actual_location = new_location
                log.save(update_fields=['actual_location'])


def reverse_fix_location_names(apps, schema_editor):
    """
    Reverse migration - convert back to old form values
    (Though this isn't recommended as it reintroduces the bug)
    """
    IrradiationRequestForm = apps.get_model('irradiation', 'IrradiationRequestForm')
    SampleIrradiationLog = apps.get_model('irradiation', 'SampleIrradiationLog')

    # Reverse mapping
    location_mapping = {
        'bare_rabbit': 'bare_rabbit_tube',
        'cad_rabbit': 'cadmium_rabbit_tube',
        'beam_port': 'beam_port',
        'thermal_column': 'thermal_column',
        'other': 'other',
    }

    # Fix IRF irradiation_location field
    for irf in IrradiationRequestForm.objects.all():
        if irf.irradiation_location:
            locations = [loc.strip() for loc in irf.irradiation_location.split(',')]
            fixed_locations = []
            changed = False

            for loc in locations:
                if loc in location_mapping:
                    fixed_loc = location_mapping[loc]
                    if fixed_loc != loc:
                        changed = True
                    fixed_locations.append(fixed_loc)
                else:
                    fixed_locations.append(loc)

            if changed:
                irf.irradiation_location = ', '.join(fixed_locations)
                irf.save(update_fields=['irradiation_location'])

    # Fix SampleIrradiationLog actual_location field
    for log in SampleIrradiationLog.objects.all():
        if log.actual_location and log.actual_location in location_mapping:
            new_location = location_mapping[log.actual_location]
            if new_location != log.actual_location:
                log.actual_location = new_location
                log.save(update_fields=['actual_location'])


class Migration(migrations.Migration):

    dependencies = [
        ("irradiation", "0008_allow_duplicate_irf_numbers"),
    ]

    operations = [
        migrations.RunPython(fix_location_names, reverse_fix_location_names),
    ]
