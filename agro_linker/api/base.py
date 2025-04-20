from ninja import NinjaAPI
from ninja.security import APIKeyHeader

class ApiKeyAuth(APIKeyHeader):
    def authenticate(self, request, key):
        # Your auth logic
        pass

def create_api(version, namespace):
    return NinjaAPI(
        version=version,
        urls_namespace=namespace,
        auth=[ApiKeyAuth()],
        csrf=True
    )