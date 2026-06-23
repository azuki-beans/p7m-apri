import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Conversion",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True,
                        serialize=False,
                        default=uuid.uuid4,
                        editable=False,
                    ),
                ),
                ("original_name", models.CharField(max_length=255)),
                ("output_name", models.CharField(max_length=255)),
                ("content", models.BinaryField()),
                (
                    "content_type",
                    models.CharField(
                        default="application/octet-stream", max_length=100
                    ),
                ),
                ("verified", models.BooleanField(default=False)),
                ("signer", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
