from django.db import models

class Watchlist(models.Model):
    ts_code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.ts_code})"
