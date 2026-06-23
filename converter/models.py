import uuid

from django.db import models


class Conversion(models.Model):
    """File estratto temporaneamente, pronto per il download.

    Il contenuto è salvato come BLOB in SQLite e ripulito dopo un'ora
    (vedi converter.views): nessun file persiste su disco.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_name = models.CharField(max_length=255)
    output_name = models.CharField(max_length=255)
    content = models.BinaryField()
    content_type = models.CharField(
        max_length=100, default="application/octet-stream"
    )
    verified = models.BooleanField(default=False)
    signer = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
