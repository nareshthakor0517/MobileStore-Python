import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import store.routing  # your websocket routes

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MobileStore.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            store.routing.websocket_urlpatterns
        )
    ),
})
