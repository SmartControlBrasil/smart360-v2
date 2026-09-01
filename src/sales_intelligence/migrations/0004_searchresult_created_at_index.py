from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sales_intelligence", "0003_campaignprospect"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="searchresult",
            index=models.Index(fields=["created_at", "id"], name="si_result_created_idx"),
        ),
    ]
