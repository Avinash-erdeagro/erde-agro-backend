from decimal import Decimal

from django.db import migrations


def seed_satellite_plans(apps, schema_editor):
    SatellitePlan = apps.get_model("billingapp", "SatellitePlan")

    plans = [
        {
            "name": "120 Days (4 Months)",
            "duration_days": 120,
            "duration_months": 4,
            "base_price_per_acre": Decimal("198.00"),
            "gst_percent": Decimal("18.00"),
            "total_price_per_acre": Decimal("234.00"),
            "commission_percent": Decimal("10.00"),
            "commission_amount_per_acre": Decimal("19.80"),
            "commission_gst_per_acre": Decimal("3.56"),
            "total_commission_per_acre": Decimal("23.36"),
            "is_active": True,
        },
        {
            "name": "180 Days (6 Months)",
            "duration_days": 180,
            "duration_months": 6,
            "base_price_per_acre": Decimal("261.00"),
            "gst_percent": Decimal("18.00"),
            "total_price_per_acre": Decimal("308.00"),
            "commission_percent": Decimal("12.50"),
            "commission_amount_per_acre": Decimal("32.63"),
            "commission_gst_per_acre": Decimal("5.87"),
            "total_commission_per_acre": Decimal("38.50"),
            "is_active": True,
        },
        {
            "name": "270 Days (9 Months)",
            "duration_days": 270,
            "duration_months": 9,
            "base_price_per_acre": Decimal("338.00"),
            "gst_percent": Decimal("18.00"),
            "total_price_per_acre": Decimal("399.00"),
            "commission_percent": Decimal("16.00"),
            "commission_amount_per_acre": Decimal("54.08"),
            "commission_gst_per_acre": Decimal("9.73"),
            "total_commission_per_acre": Decimal("63.81"),
            "is_active": True,
        },
        {
            "name": "365 Days (12 Months)",
            "duration_days": 365,
            "duration_months": 12,
            "base_price_per_acre": Decimal("381.00"),
            "gst_percent": Decimal("18.00"),
            "total_price_per_acre": Decimal("450.00"),
            "commission_percent": Decimal("20.00"),
            "commission_amount_per_acre": Decimal("76.20"),
            "commission_gst_per_acre": Decimal("13.72"),
            "total_commission_per_acre": Decimal("89.92"),
            "is_active": True,
        },
    ]

    for plan in plans:
        SatellitePlan.objects.update_or_create(
            duration_days=plan["duration_days"],
            defaults=plan,
        )


def unseed_satellite_plans(apps, schema_editor):
    SatellitePlan = apps.get_model("billingapp", "SatellitePlan")
    SatellitePlan.objects.filter(duration_days__in=[120, 180, 270, 365]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("billingapp", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_satellite_plans, unseed_satellite_plans),
    ]
