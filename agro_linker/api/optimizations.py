# # api/optimizations.py
# from ninja.operation import PathView
# from django.core.cache import caches
# from ninja import NinjaAPI
# from django.conf import settings

# class CachedAPI(NinjaAPI):
#     def create_response(self, request, result, *, status=200):
#         cache_key = f"api:{request.path}:{request.GET.urlencode()}"
#         if request.method == "GET":
#             if cached := caches["api"].get(cache_key):
#                 return cached
#             response = super().create_response(request, result, status=status)
#             caches["api"].set(cache_key, response, 60*5)  # 5 min cache
#             return response
#         return super().create_response(request, result, status=status)
