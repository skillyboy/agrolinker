# agro_linker/urls.py
from django.urls import path
from .api.v1.api import api

urlpatterns = [
    path("api/", api.urls),  # Django Ninja automatically generates URL patterns
]
