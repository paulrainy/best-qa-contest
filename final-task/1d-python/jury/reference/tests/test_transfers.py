def test_readiness_and_read_only_connections(api, db):
    assert api.get("/api/v1/health")["status"] == "UP"
    assert db.select("SELECT 1 AS ready")[0]["ready"] == 1
