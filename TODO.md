# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO34

## TODO32

`next` (the post-login redirect target) has no open-redirect
validation anywhere: `ktp_controller/wui/auth_routes.py`'s
`_get_login`/`_post_login`/`_post_locale` take it straight from the
query string or form field and feed it into `RedirectResponse(url=...)`
unchecked. Found while fixing the htmx `HX-Current-URL`-based `next`
redirect in `ktp_controller/wui/main.py`'s `_handle_not_authenticated`
(2026-11-06) - that fix doesn't make this worse, but the underlying gap
is pre-existing and still open. Should validate `next` is a relative,
same-origin path before redirecting to it.
