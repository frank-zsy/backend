"""URL configuration for points app."""

from django.urls import path

from . import views

app_name = "points"

urlpatterns = [
    path("points/", views.my_points, name="my_points"),
]
