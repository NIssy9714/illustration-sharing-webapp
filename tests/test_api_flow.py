def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


def test_register_login_create_like_delete_flow(client):
    # register
    r = client.post("/auth/register", json={"username": "u1", "password": "password123"})
    assert r.status_code == 201
    user = r.json()
    assert user["username"] == "u1"

    # login
    r = client.post("/auth/login", json={"username": "u1", "password": "password123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # create post
    r = client.post(
        "/posts",
        json={"title": "hello", "body": "body", "filename": None},
        headers=headers,
    )
    assert r.status_code == 201
    post = r.json()
    post_id = post["id"]
    assert post["title"] == "hello"

    # list posts
    r = client.get("/posts")
    assert r.status_code == 200
    assert any(p["id"] == post_id for p in r.json())

    # toggle like on
    r = client.post(f"/posts/{post_id}/likes/toggle", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["liked"] is True
    assert data["like_count"] == 1

    # toggle like off
    r = client.post(f"/posts/{post_id}/likes/toggle", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["liked"] is False
    assert data["like_count"] == 0

    # delete post
    r = client.delete(f"/posts/{post_id}", headers=headers)
    assert r.status_code == 204

    # get post -> 404
    r = client.get(f"/posts/{post_id}")
    assert r.status_code == 404


def test_auth_required(client):
    r = client.post("/posts", json={"title": "x", "body": None, "filename": None})
    assert r.status_code == 401

