# agro_linker/urls.py
from django.urls import path
from .api import api

urlpatterns = [
    path("", api.urls),  # All APIs live under /api/v1/
]
