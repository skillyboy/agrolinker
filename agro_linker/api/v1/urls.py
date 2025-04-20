# agro_linker/urls.py
from django.urls import path
from .router import api

urlpatterns = [
    path("api/v1/", api.urls),
]