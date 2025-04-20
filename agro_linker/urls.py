# agro_linker/urls.py
from django.urls import path
from .api.v1 import api

urlpatterns = [
    path("api/v1/", api.urls),
]
