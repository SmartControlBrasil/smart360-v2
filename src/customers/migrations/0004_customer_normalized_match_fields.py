from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0003_customerassignmenttransfer"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="normalized_phone",
            field=models.CharField(blank=True, db_index=True, default="", editable=False, max_length=32),
        ),
        migrations.AddField(
            model_name="customer",
            name="normalized_whatsapp",
            field=models.CharField(blank=True, db_index=True, default="", editable=False, max_length=32),
        ),
        migrations.AddField(
            model_name="customer",
            name="normalized_domain",
            field=models.CharField(blank=True, db_index=True, default="", editable=False, max_length=255),
        ),
    ]
