import json

from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


class AppConsumer(AsyncWebsocketConsumer):
    group_name = 'app_updates'

    async def connect(self):
        query = self.scope['query_string'].decode()
        token = None
        for part in query.split('&'):
            if part.startswith('token='):
                token = part.split('=', 1)[1]
                break

        if not token:
            await self.close(code=4001)
            return

        try:
            access = AccessToken(token)
            self.user_id = access['user_id']
        except TokenError:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({'type': 'connected'}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def app_broadcast(self, event):
        await self.send(text_data=json.dumps(event['message']))
