from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/app/', consumers.AppConsumer.as_asgi()),
]
