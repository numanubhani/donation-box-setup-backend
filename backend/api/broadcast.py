from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def emit_event(event_type: str, payload=None, resource: str | None = None):
    """Push a realtime event to all connected WebSocket clients."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    message = {'type': event_type}
    if payload is not None:
        message['payload'] = payload
    if resource is not None:
        message['resource'] = resource

    async_to_sync(channel_layer.group_send)(
        'app_updates',
        {
            'type': 'app_broadcast',
            'message': message,
        },
    )
