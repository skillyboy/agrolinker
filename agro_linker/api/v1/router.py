# agro_linker/api/v1/router.py
def register_v1_routers(api):
    """Register all version 1 endpoints"""
    from ..market import router as market_router
    from ..orders import router as orders_router
    from ..chat import router as chat_router
    from ..bid import router as bid_router
    from ..weather import router as weather_router
    from ..notification import router as notification_router
    from ..auth import router as auth_router

    # Register routes with tags
    api.add_router("/market/", market_router, tags=["Market"])
    api.add_router("/orders/", orders_router, tags=["Orders"])
    api.add_router("/chat/", chat_router, tags=["Chat"])
    api.add_router("/bid/", bid_router, tags=["Bidding"])
    api.add_router("/weather/", weather_router, tags=["Weather"])
    api.add_router("/notification/", notification_router, tags=["Notifications"])
    api.add_router("/auth/", auth_router, tags=["Authentication"])
    