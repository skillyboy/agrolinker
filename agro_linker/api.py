# agro_linker/api/api.py
from ninja.security import APIKeyHeader
from ninja import NinjaAPI
from agro_linker.schemas import *
from agro_linker.models import *

class ApiKeyAuth(APIKeyHeader):
    def authenticate(self, request, key):
        from agro_linker.models import APIToken
        try:
            return APIToken.objects.get(key=key).user
        except APIToken.DoesNotExist:
            return None

# Create single API instance
api = NinjaAPI(
    title="Agro Linker API",
    version="2.0",
    auth=[ApiKeyAuth()],
    docs_decorator=lambda f: f,
    csrf=True,
    urls_namespace="api_current"
)



def register_all_routers():
    """Register all API routers"""
    from agro_linker.api.v1.router import register_v1_routers
    register_v1_routers(api)

register_all_routers()