# Generated manually - adds ActivationTimeline model for tracking intermediate activation states

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('irradiation', '0012_normalize_location_values'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivationTimeline',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('step_number', models.IntegerField(help_text='Sequential step number (0=initial, 1=after first irr, etc.)')),
                ('step_type', models.CharField(choices=[('initial', 'Initial State'), ('irradiation', 'After Irradiation'), ('decay', 'After Decay Period'), ('current', 'Current Date')], help_text='Type of timeline step', max_length=20)),
                ('step_datetime', models.DateTimeField(help_text='Date/time of this step in the timeline')),
                ('description', models.CharField(help_text='Human-readable description of this step', max_length=200)),
                ('inventory', models.JSONField(help_text='Isotopic inventory (atoms) at this step: {isotope: n_atoms}')),
                ('total_activity_bq', models.DecimalField(decimal_places=4, help_text='Total activity at this step (Bq)', max_digits=20)),
                ('dominant_isotopes', models.JSONField(blank=True, help_text='Top isotopes by activity: {isotope: activity_bq}', null=True)),
                ('estimated_dose_rate_1ft', models.DecimalField(blank=True, decimal_places=2, help_text='Estimated dose rate at 1 foot (mrem/hr)', max_digits=10, null=True)),
                ('decay_time_seconds', models.BigIntegerField(blank=True, help_text='Decay time in seconds (for decay steps)', null=True)),
                ('activation_result', models.ForeignKey(help_text='Parent activation result this timeline belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='timeline_entries', to='irradiation.activationresult')),
                ('irradiation_log', models.ForeignKey(blank=True, help_text='Irradiation log if this step follows an irradiation', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='timeline_entries', to='irradiation.sampleirradiationlog')),
            ],
            options={
                'verbose_name': 'Activation Timeline Entry',
                'verbose_name_plural': 'Activation Timeline Entries',
                'ordering': ['activation_result', 'step_number'],
                'unique_together': {('activation_result', 'step_number')},
            },
        ),
    ]
