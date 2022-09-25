from http import HTTPStatus
from http.client import HTTPResponse
from urllib import request
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, CreateModelMixin
from rest_framework.parsers import MultiPartParser
from GPSPhoto import gpsphoto
from rest_framework.response import Response
from .serializers import PhotoSerializer
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework import status
from .models import Path
from .serializers import PathSerializer
import pandas as pd
import math

# Create your views here.
class Get(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES["filename"]
        path = default_storage.save(
            "files/heart_of_the_swarm.jpg", ContentFile(file.read())
        )
        print(path)
        data = gpsphoto.getGPSData(path)
        print(data)
        try:
            lat, long = data["Latitude"], data["Longitude"]
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = PhotoSerializer(data=data)
        if serializer.is_valid():
            return Response(serializer.data)
        return HTTPResponse("Powel naxy")


class Add(GenericAPIView, CreateModelMixin):
    parser_classes = [MultiPartParser]
    serializer_class = PathSerializer

    def post(self, request):
        xl = request.FILES["filename"]
        parse(xl)
        t = Path.objects.all()
        print(t)
        serializer = PathSerializer(data=t)
        if serializer.is_valid():
            return Response(serializer.data)
        return Response(status=status.HTTP_201_CREATED)


class Parse(GenericAPIView, ListModelMixin):
    serializer_class = PathSerializer
    slide = 1

    def get(self, request, slide, *args, **kwargs):
        self.slide = slide
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return Path.objects.filter(slide=self.slide)


def parse(xl):
    _slide = 0
    if Path.objects.last():
        _slide += Path.objects.last().slide + 1
    sheetnames = pd.ExcelFile(xl).sheet_names
    for i in sheetnames:
        sheet = pd.read_excel(xl, sheet_name=i)
        t = 0
        temporary = sheet.iloc[t]
        while not temporary.empty:
            print(temporary)
            array = temporary.array
            latitude = array[0]
            longtitude = array[1]
            altitude = array[2]
            identifier = array[3]
            if not math.isnan(array[4]):
                timestamp = array[4]
            else:
                timestamp = 0
            if not math.isnan(array[5]):
                floor_label = array[5]
            else:
                floor_label = None
            horizontal_accuracy = array[6]
            vertical_accuracy = array[7]
            confidence = array[8]
            activity = array[9]
            slide = _slide
            p = Path(
                latitude=latitude,
                longtitude=longtitude,
                altitude=altitude,
                identifier=identifier,
                timestamp=timestamp,
                floor_label=floor_label,
                horizontal_accuracy=horizontal_accuracy,
                vertical_accuracy=vertical_accuracy,
                confidence=confidence,
                activity=activity,
                slide=slide,
            )
            p.save()
            t += 1
            try:
                temporary = sheet.iloc[t]
            except:
                break
        _slide += 1
    # sheetnames = pd.ExcelFile(xl).sheet_names
    # for i in sheetnames:
    #     # Read and store content
    #     # of an excel file
    #     read_file = pd.read_excel(xl, sheet_name=i)

    #     # Write the dataframe object
    #     # into csv file
    #     read_file.to_csv("test.csv", index=None, header=False)

    #     with open("test.csv", "r") as cs:
    #         datareader = csv.reader(cs)
    #         for row in datareader:
    #             for cell in row:
    #                 print(cell)
