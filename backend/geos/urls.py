from django.urls import path
from .views import Get, Parse, Add

urlpatterns = [
    path("", Get.as_view()),
    path("parse/<int:slide>/", Parse.as_view()),
    path("parse/add/", Add.as_view()),
]
