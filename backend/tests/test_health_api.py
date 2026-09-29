"""Health endpoint tests."""


async def test_liveness(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


async def test_readiness_reports_database_and_redis(client):
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["components"]["database"] == "up"
    assert body["components"]["redis"] == "up"


async def test_openapi_documentation_served(client):
    """Requirement: Swagger documentation for all endpoints."""
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/register" in paths
    # every documented path carries summaries (Swagger quality)
    for path, ops in paths.items():
        for method, op in ops.items():
            if method in ("get", "post", "patch", "put", "delete"):
                assert "summary" in op, f"{method.upper()} {path} lacks a summary"
