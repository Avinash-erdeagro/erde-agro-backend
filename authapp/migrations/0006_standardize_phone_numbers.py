from django.conf import settings
from django.core.validators import RegexValidator
from django.db import migrations, models


def normalize_indian_phone_number(phone_number):
    phone_number = phone_number.strip().replace(" ", "")

    if phone_number.startswith("+91") and len(phone_number) == 13 and phone_number[1:].isdigit():
        return phone_number

    if len(phone_number) == 10 and phone_number.isdigit():
        return f"+91{phone_number}"

    return phone_number


def forwards(apps, schema_editor):
    FarmerProfile = apps.get_model("authapp", "FarmerProfile")
    FpoProfile = apps.get_model("authapp", "FpoProfile")
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)

    for farmer in FarmerProfile.objects.select_related("app_user__user"):
        normalized_contact = normalize_indian_phone_number(farmer.contact_number)
        if farmer.contact_number != normalized_contact:
            farmer.contact_number = normalized_contact
            farmer.save(update_fields=["contact_number"])

        user = getattr(getattr(farmer, "app_user", None), "user", None)
        if user and user.username != normalized_contact:
            user.username = normalized_contact
            user.save(update_fields=["username"])

    for fpo in FpoProfile.objects.all():
        normalized_mobile = normalize_indian_phone_number(fpo.mobile)
        if fpo.mobile != normalized_mobile:
            fpo.mobile = normalized_mobile
            fpo.save(update_fields=["mobile"])


class Migration(migrations.Migration):

    dependencies = [
        ("authapp", "0005_remove_farmerprofile_email"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="farmerprofile",
            name="contact_number",
            field=models.CharField(
                max_length=13,
                validators=[
                    RegexValidator(
                        regex=r"^\+91\d{10}$",
                        message="Phone number must be stored in +91XXXXXXXXXX format.",
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="fpoprofile",
            name="mobile",
            field=models.CharField(
                max_length=13,
                validators=[
                    RegexValidator(
                        regex=r"^\+91\d{10}$",
                        message="Phone number must be stored in +91XXXXXXXXXX format.",
                    )
                ],
            ),
        ),
    ]
