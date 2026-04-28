import pytest

@pytest.mark.parametrize("route", [
    "/",
    "/printers",
    "/printers/monitor",
    "/filaments",
    "/calculator",
    "/history",
    "/settings",
    "/shpoolken",
    "/about",
])
def test_smoke_get_routes(client, route):
    """Smoke test: all main GET routes should return 200."""
    resp = client.get(route, follow_redirects=True)
    assert resp.status_code == 200, f"Route {route} returned {resp.status_code}"

def test_404_handler(client):
    """Custom 404 handler should return 404 with error template."""
    resp = client.get("/nonexistent-page")
    assert resp.status_code == 404
    assert b"404" in resp.data

def test_static_file(client):
    """Static CSS should be served."""
    resp = client.get("/static/style.css")
    assert resp.status_code == 200
    assert b"body" in resp.data or b"{" in resp.data

def test_theme_css(client):
    """Theme CSS endpoint should return CSS."""
    resp = client.get("/theme.css?preset=modern&theme=light&glass=1")
    assert resp.status_code == 200
    assert b":root" in resp.data
