# 冒煙測試：不需資料庫即可驗證的端點與內部密鑰驗證


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_internal_endpoint_requires_secret(client):
    resp = client.post("/api/roast/", json={})
    assert resp.status_code == 401


def test_internal_endpoint_rejects_wrong_secret(client):
    resp = client.post("/api/roast/", json={}, headers={"X-Internal-Secret": "wrong"})
    assert resp.status_code == 401
