from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api.v1.router import register_v1_routers
from .views import index
from django.conf import settings
from django.conf.urls.static import static


router = DefaultRouter()

register_v1_routers(router)



urlpatterns = [
    path('', index, name='index'),
    path('api/v1/', include(router.urls)),
]


