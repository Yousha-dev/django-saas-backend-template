# routing.py
"""
WebSocket URL routing for real-time features.

Configure your WebSocket consumers here. Examples provided below
can be replaced with your application-specific WebSocket routes.
"""

# Import your consumers here
# from myapp import consumers

websocket_urlpatterns = [
    # Example: Real-time notifications
    # re_path(r'^ws/notifications/(?P<user_id>\w+)/?$',
    #         consumers.NotificationConsumer.as_asgi()),
    # Example: Live data stream
    # re_path(r'^ws/stream/(?P<channel>\w+)/?$',
    #         consumers.StreamConsumer.as_asgi()),
    # Example: Task/job monitoring
    # re_path(r'^ws/tasks/monitor/(?P<task_id>\w+)/?$',
    #         consumers.TaskMonitorConsumer.as_asgi()),
]
