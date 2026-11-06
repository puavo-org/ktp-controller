def test_unauthenticated_htmx_request_redirects_to_hx_current_url(wui_client):
    # The htmx request that tripped the auth check targets its own small
    # endpoint (e.g. a /nav_status background poll), not the page the
    # browser is actually showing. HX-Current-URL carries the browser's
    # real location, so "next" should come from that, not from the
    # request's own path.
    response = wui_client.get(
        "/",
        headers={
            "HX-Request": "true",
            "HX-Current-URL": "https://testserver/invigilator/",
        },
    )

    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == "/login?next=%2Finvigilator%2F"


def test_unauthenticated_htmx_request_without_hx_current_url_falls_back_to_request_path(
    wui_client,
):
    response = wui_client.get("/", headers={"HX-Request": "true"})

    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == "/login?next=%2F"


def test_unauthenticated_non_htmx_request_ignores_hx_current_url(wui_client):
    # Real browser navigations never send HX-Current-URL, but guard
    # against it being misused if some client did send it - "next" must
    # still track the request's own path in that branch.
    response = wui_client.get(
        "/", headers={"HX-Current-URL": "https://testserver/invigilator/"}
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=%2F"


def test_static_file_served_through_forwarded_prefix(wui_client):
    # Regression test: StaticFiles is mounted (APP.mount), and a Mount
    # accumulates root_path for its child scope rather than stripping its
    # own prefix from scope["path"] - it relies on nginx forwarding the
    # full, un-stripped path (see
    # ktp_controller.nginx.enable_nginx_wui_tls_reverse_proxy) so Starlette
    # can recompute the mount-relative path on the fly. Forwarding an
    # already-stripped path here previously made every static asset 404
    # once a prefix was in play.
    response = wui_client.get(
        "/remote/12345/static/pico.min.css",
        headers={"X-Forwarded-Prefix": "/remote/12345"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/css; charset=utf-8"
