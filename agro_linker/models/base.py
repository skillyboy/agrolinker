from django.db import models

class BaseIntegration(models.Model):
    class Meta:
        abstract = True


