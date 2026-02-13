import logging
import threading
from functools import wraps

from django.core.cache import cache
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def cached_response_with_background_update(cache_key_prefix, timeout=86400):
    def decorator(view_method):
        @wraps(view_method)
        def wrapped_view(view_instance, request, *args, **kwargs):
            user_id = getattr(request, "user_id", None)
            if not user_id:
                return view_method(view_instance, request, *args, **kwargs)

            cache_key = f"{cache_key_prefix}:{user_id}"
            cached_data = cache.get(cache_key)

            if cached_data is not None:

                def update_cache():
                    try:
                        response = view_method(view_instance, request, *args, **kwargs)
                        cache.set(cache_key, response.data, timeout)
                    except Exception as e:
                        logger.error(f"Cache update failed for {cache_key}: {e!s}")

                thread = threading.Thread(target=update_cache)
                thread.daemon = True
                thread.start()

                return Response(cached_data)

            response = view_method(view_instance, request, *args, **kwargs)
            cache.set(cache_key, response.data, timeout)
            return response

        return wrapped_view

    return decorator
