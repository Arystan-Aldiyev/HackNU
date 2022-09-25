from rest_framework import serializers
from .models import Path


class PhotoSerializer(serializers.Serializer):
    Latitude = serializers.FloatField()
    Longitude = serializers.FloatField()


class PathSerializer(serializers.ModelSerializer):
    class Meta:
        queryset = Path.objects.all()
        model = Path
        fields = [
            "id",
            "latitude",
            "longtitude",
            "altitude",
            "identifier",
            "timestamp",
            "floor_label",
            "horizontal_accuracy",
            "vertical_accuracy",
            "confidence",
            "activity",
            "slide",
        ]
