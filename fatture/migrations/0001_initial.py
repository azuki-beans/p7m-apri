import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Fattura",
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
