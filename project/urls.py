# project/urls.py
from django.urls import path
from agro_linker.api.api import api

urlpatterns = [
    path("api/", api.urls),
]