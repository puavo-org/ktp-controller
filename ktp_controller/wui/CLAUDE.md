# WUI conventions

- Every `POST /actions/<name>` endpoint (in `ktp_controller/wui/actions/`)
  is gated by its own `wui.actions.<name>` permission, checked via the
  `require_permission` decorator and granted to roles through its own
  Alembic migration (see `alembic/versions/*_add_wui_actions_*`). The
  invigilator template also gets a matching `can_<name>` context flag
  (set in `ktp_controller/wui/invigilator/routes.py`) controlling
  whether the corresponding button/control renders at all.

- Translatable strings (`_()`/`{% trans %}` in Python and `.j2`
  templates) require running `make i18n-extract`, `make i18n-update`,
  and `make i18n-compile` (in that order) to add/refresh the `fi`/`sv`/`en`
  `.po`/`.mo` files before `make check`'s `check-i18n` target will pass.

- To visually verify a WUI CSS/template change, run `./dev-run`,
  then log in and screenshot pages headlessly with
  `uv run aux/wui_screenshot.py --username <user> --password '<password>'
  <path> [<path> ...]` (paths are WUI routes, e.g. `/invigilator/`,
  `/invigilator/student_access_code`, `/`). Pass `--expand-details` to
  force-open `<details>` elements (e.g. exam groups) before capturing.
  Screenshots are written to `workdirs/dev/screenshots/` by default
  (override with `--out-dir`). The `valvoja` (invigilator) user always
  exists in dev-run; get its password with `uv run python -c "import
  ktp_controller.abitti2.naksu2; print(ktp_controller.abitti2.naksu2.read_supervisor_passphrase())"`.
  For any other user, ask me for credentials rather than reading them
  out of `workdirs/dev/ktp_controller.env` or similar files yourself —
  that's treated as credential material. Shut `dev-run` down afterwards
  with `./dev-run shutdown-wait`.
