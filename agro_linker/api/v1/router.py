# agro_linker/api/v1/router.py

from ninja import Router

# Import sub-routers
from . import auth, bid, chat, farm, market, notification, orders, thrift_service, weather, whatsapp


# Create a master router
router = Router()

# Register your sub-routers
router.add_router("/auth/", auth.router)
router.add_router("/bid/", bid.router)
router.add_router("/chat/", chat.router)
router.add_router("/farm/", farm.router)
router.add_router("/market/", market.router)
router.add_router("/notification/", notification.router)
router.add_router("/orders/", orders.router)
router.add_router("/thrift/", thrift_service.router)
router.add_router("/weather/", weather.router)
router.add_router("/whatsapp/", whatsapp.router)
