# agro_linker/api/api.py
from ninja import NinjaAPI
from .router import router
from ninja.security import APIKeyHeader

class ApiKeyAuth(APIKeyHeader):
    def authenticate(self, request, key):
        from agro_linker.models.models import APIToken
        try:
            return APIToken.objects.get(key=key).user
        except APIToken.DoesNotExist:
            return None

# Create the API instance
api = NinjaAPI(
    title="Agro Linker API",
    version="2.0",
    auth=[ApiKeyAuth()],
    docs_url="/docs",   # exposed at /api/v1/docs
    openapi_url="/openapi.json",
    csrf=True,
    urls_namespace="api_current"
)

# Register your central router
api.add_router("v1/", router)