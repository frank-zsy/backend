"""Rename user_profile field to user in PointSource and PointTransaction models."""

from django.db import migrations


class Migration(migrations.Migration):
    """Rename user_profile to user for better clarity."""

    dependencies = [
        ("points", "0006_alter_pointsource_options"),
    ]

    operations = [
        migrations.RenameField(
            model_name="pointsource",
            old_name="user_profile",
            new_name="user",
        ),
        migrations.RenameField(
            model_name="pointtransaction",
            old_name="user_profile",
            new_name="user",
        ),
    ]
