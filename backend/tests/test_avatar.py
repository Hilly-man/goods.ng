from tests.conftest import png_bytes


def test_upload_replace_and_remove_profile_photo(make_user):
    u = make_user()
    assert u.get("/auth/me").json()["avatar_url"] is None
    r = u.post("/users/me/avatar", files={"file": ("me.png", png_bytes(), "image/png")})
    assert r.status_code == 200, r.text
    url = r.json()["avatar_url"]
    assert url and url.endswith(".webp")
    assert u.get("/auth/me").json()["avatar_url"] == url
    r = u.delete("/users/me/avatar")
    assert r.status_code == 200 and r.json()["avatar_url"] is None


def test_avatar_rejects_non_images(make_user):
    u = make_user()
    r = u.post("/users/me/avatar", files={"file": ("x.png", b"not an image", "image/png")})
    assert r.status_code == 400 or r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_image"


def test_avatar_requires_sign_in(client):
    assert client.post("/api/v1/users/me/avatar", files={"file": ("me.png", png_bytes(), "image/png")}).status_code == 401
