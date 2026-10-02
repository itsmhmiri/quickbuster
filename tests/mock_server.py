"""Local mock server simulating dynamic soft-404s, redirects, and endpoints."""

import time
from aiohttp import web


async def handle_root(request: web.Request) -> web.Response:
    return web.Response(text="Welcome to the Mock Target Application", status=200)


async def handle_admin(request: web.Request) -> web.Response:
    return web.Response(text="<html><body>Secret Admin Panel</body></html>", status=200)


async def handle_login(request: web.Request) -> web.Response:
    return web.Response(text="<html><body>Login Page</body></html>", status=200)


async def handle_redirect(request: web.Request) -> web.Response:
    raise web.HTTPFound("/login.php")


async def handle_catchall(request: web.Request) -> web.Response:
    # Dynamic Soft-404 returning 200 OK with timestamp to simulate dynamic length variation
    body = f"Custom 404: Page Not Found. Current Time: {time.time():.4f}"
    return web.Response(text=body, status=200)


def create_mock_app() -> web.Application:
    """Create and configure the aiohttp mock web application."""
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/admin", handle_admin)
    app.router.add_get("/login.php", handle_login)
    app.router.add_get("/redirect", handle_redirect)
    # Wildcard catch-all route for any undefined path
    app.router.add_get("/{tail:.*}", handle_catchall)
    return app


if __name__ == "__main__":
    app = create_mock_app()
    web.run_app(app, host="127.0.0.1", port=8888)
