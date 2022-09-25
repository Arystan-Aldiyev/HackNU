from django.db import models


# Create your models here.
class Path(models.Model):
    latitude = models.FloatField()
    longtitude = models.FloatField()
    altitude = models.FloatField()
    identifier = models.CharField(max_length=150, null=True, blank=True)
    timestamp = models.IntegerField()
    floor_label = models.IntegerField(null=True, blank=True)
    horizontal_accuracy = models.FloatField()
    vertical_accuracy = models.FloatField()
    confidence = models.FloatField(default=0.6827)
    activity = models.CharField(max_length=100)
    slide = models.IntegerField()
