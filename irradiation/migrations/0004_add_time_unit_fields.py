# Generated migration file for adding time unit fields to SampleIrradiationLog

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('irradiation', '0003_irradiationrequestform_change_notes_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='sampleirradiationlog',
            name='total_time_unit',
            field=models.CharField(
                choices=[('min', 'minutes'), ('hr', 'hours'), ('sec', 'seconds')],
                default='min',
                help_text='Unit for total time',
                max_length=10
            ),
        ),
        migrations.AddField(
            model_name='sampleirradiationlog',
            name='decay_time_unit',
            field=models.CharField(
                choices=[('min', 'minutes'), ('hr', 'hours'), ('sec', 'seconds')],
                default='min',
                help_text='Unit for decay time',
                max_length=10
            ),
        ),
    ]
