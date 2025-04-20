# agro_linker/api/v1/router.py
from ninja import NinjaAPI

from agro_linker.api import auth, bid, chat, farm, market, microfinance, notification, orders, thrift_service, weather, whatsapp

api = NinjaAPI(title="AgroLinker API", version="1.0")

# Mount all sub-routers under organized prefixes
api.add_router("/auth/", auth.router)
api.add_router("/bid/", bid.router)
api.add_router("/chat/", chat.router)
api.add_router("/farm/", farm.router)
api.add_router("/market/", market.router)
api.add_router("/microfinance/", microfinance.router)
api.add_router("/notification/", notification.router)
api.add_router("/orders/", orders.router)
api.add_router("/thrift/", thrift_service.router)
api.add_router("/weather/", weather.router)
api.add_router("/whatsapp/", whatsapp.router)
