def test_create_get_only(client):
    ok = client.get("/create")
    assert ok.status_code == 200
    bad = client.post("/create")
    assert bad.status_code == 405
