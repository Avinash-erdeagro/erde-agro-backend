from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("satelliteapp", "0002_satellitefarmalert_satellitefarmnotification"),
    ]

    operations = [
        migrations.AddField(
            model_name="satellitefarmnotification",
            name="push_status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("SENT", "Sent"),
                    ("FAILED", "Failed"),
                    ("NO_DEVICES", "No Devices"),
                ],
                default="PENDING",
                db_index=True,
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="satellitefarmnotification",
            name="push_failure_reason",
            field=models.TextField(blank=True, default=""),
        ),
    ]
