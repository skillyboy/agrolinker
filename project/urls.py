# project/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('agro_linker.api.v1.urls')),
    # path('api/v1', include('agro_linker.urls')),
    # path('api/', include('agro_linker.api.v1.api.urls')),  
]
