# Generated manually for IRF amendment improvements

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("irradiation", "0007_fluxconfiguration_activationresult_samplecomposition"),
    ]

    operations = [
        migrations.AlterField(
            model_name="irradiationrequestform",
            name="irf_number",
            field=models.CharField(
                max_length=20,
                help_text="Sequential number following last two digits of year (e.g. 95-1, 95-2)",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="irradiationrequestform",
            unique_together={("irf_number", "version_number")},
        ),
        migrations.AlterModelOptions(
            name="irradiationrequestform",
            options={
                "ordering": ["-irf_number", "-version_number"],
                "verbose_name": "Irradiation Request Form",
                "verbose_name_plural": "Irradiation Request Forms",
            },
        ),
    ]
