"""URL configuration for homepage app."""

from django.urls import path

from .views import index, user_search

app_name = "homepage"

urlpatterns = [
    path("", index, name="index"),
    path("search/", user_search, name="search"),
]
