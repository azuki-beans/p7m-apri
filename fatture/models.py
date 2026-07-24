import uuid

from django.db import models


class Fattura(models.Model):
    """PDF di una fattura, generato al volo e conservato temporaneamente.

    Come per converter.Conversion, il contenuto è un BLOB in SQLite ripulito
    dopo un'ora (vedi fatture.views): nessun file resta su disco.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_name = models.CharField(max_length=255)
    output_name = models.CharField(max_length=255)
    content = models.BinaryField()  # il PDF generato
    created_at = models.DateTimeField(auto_now_add=True)
