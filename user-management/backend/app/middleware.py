"""Request logging middleware: request IDs, timing and error tracing.

For every request it:
1. reuses the client's X-Request-ID if it is a valid UUID, else makes a new one
2. times the request
3. returns the ID in the X-Request-ID response header
4. logs one line:  request_id=<id> POST /users 201 12ms
5. if the route crashes, logs the traceback with the same request ID and
   returns a generic 500, so the error can be traced from the ID alone

Only the method, path and status are logged, never bodies, query strings
or headers, so passwords and tokens cannot leak into the logs.
"""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.requests")

REQUEST_ID_HEADER = "X-Request-ID"

CallNext = Callable[[Request], Awaitable[Response]]


def resolve_request_id(header_value: str | None) -> str:
    """Return the client's ID if it is a valid UUID, otherwise a new uuid4."""
    if header_value:
        try:
            return str(uuid.UUID(header_value))
        except ValueError:
            pass  # invalid: fall through and generate a fresh ID

    return str(uuid.uuid4())


async def request_logging_middleware(request: Request, call_next: CallNext) -> Response:
    request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
    request.state.request_id = request_id  # available to routes if needed

    start = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        # Unexpected error in a route: full details go to the server log only.
        logger.exception(
            "request_id=%s unhandled error on %s %s",
            request_id,
            request.method,
            request.url.path,
        )
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error", "request_id": request_id},
        )

    duration_ms = (time.perf_counter() - start) * 1000
    response.headers[REQUEST_ID_HEADER] = request_id

    logger.info(
        "request_id=%s %s %s %d %.0fms",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    return response
