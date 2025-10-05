"""Views for the homepage app."""

from django.shortcuts import render


def index(request):
    """Render the homepage index page."""
    return render(request, "homepage/index.html")
