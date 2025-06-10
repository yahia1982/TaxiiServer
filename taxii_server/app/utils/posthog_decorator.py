# posthog_decorator.py
import os
import time
from functools import wraps
from typing import Callable, Optional, List

from bfore_auth import get_current_user
from bfore_auth.dependencies import get_user_from_token
from fastapi import Request, HTTPException
from posthog import Posthog

posthog = Posthog(
    project_api_key=os.getenv(
        "POSTHOG_API_KEY", "phc_AKPo1E2Y1hBQDFNY4T4TN9i9ty1JVvrDAwPArqTmgKJ"
    ),
    host="https://eu.i.posthog.com",
)


def track_request(endpoint_name: Optional[str] = None):
    """
    Factory to allow passing optional custom endpoint name.
    """

    def decorator(f: Callable):
        @wraps(f)
        async def wrapped(request: Request, *args, **kwargs):
            start_time = time.time()

            # Call the actual endpoint
            result = await f(request, *args, **kwargs)

            duration_ms = (time.time() - start_time) * 1000

            # Gather properties automatically
            event_properties = {
                "endpoint": endpoint_name or f.__name__,
                "url": str(request.url),
                "path": request.url.path,
                "method": request.method,
                "status": getattr(result, "status_code", 200),
                "duration_ms": round(duration_ms, 2),
                "ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent", "unknown"),
            }

            # Example logic for extracting user info
            distinct_id = None
            user_companies: List[str] = []
            print(request.headers.get("Authorization"))
            user = get_user_from_token(request.headers.get("Authorization"))
            # Customize this part based on how you store user data in FastAPI
            # if hasattr(request.state, "user") and request.state.user:
            #     user = request.state.user
            #     distinct_id = getattr(user, "user_id", None)
            #     user_companies = getattr(user, "companies", [])
            # elif "Authorization" in request.headers:
            #     # Fallback: Use token or something from header
            #     distinct_id = request.headers.get("Authorization")
            #
            # event_properties["companies"] = user_companies

            if not distinct_id:
                distinct_id = event_properties["ip"]

            # Send event to PostHog
            try:
                posthog.capture(
                    distinct_id=distinct_id,
                    event="TAXII Event",
                    properties=event_properties,
                )
            except Exception as e:
                print(f"Failed to send event to PostHog: {e}")

            return result

        return wrapped

    return decorator
