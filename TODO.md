# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO21

## TODO1
Examine and handle currently unhandled messages from Abitti2 1.37.1:

```
Sep 26 2026 17:03:22 testvirtkan1 supervisord: ktp-controller-agent WARNING:2026-09-26 17:03:22,477:ktp_controller.agent.main:__communicate_with_abitti2:1375:unhandled 'ytl-connection' message from Abitti2: {'type': 'ytl-connection', 'data': {'status': 'no-key'}}
Sep 26 2026 17:03:22 testvirtkan1 supervisord: ktp-controller-agent WARNING:2026-09-26 17:03:22,477:ktp_controller.agent.main:__communicate_with_abitti2:1375:unhandled 'answer-send-state' message from Abitti2: {'type': 'answer-send-state', 'data': {'status': 'idle', 'sentAt': None, 'sentBy': None}}
Sep 26 2026 17:03:22 testvirtkan1 supervisord: ktp-controller-agent WARNING:2026-09-26 17:03:22,477:ktp_controller.agent.main:__communicate_with_abitti2:1375:unhandled 'answer-download-state' message from Abitti2: {'type': 'answer-download-state', 'data': None}
Sep 26 2026 17:03:29 testvirtkan1 supervisord: ktp-controller-agent WARNING:2026-09-26 17:03:29,380:ktp_controller.agent.main:__communicate_with_abitti2:1375:unhandled 'ytl-connection' message from Abitti2: {'type': 'ytl-connection', 'data': {'status': 'no-key'}}
```

## TODO2

Unify/merge `ktp_controller.wui.utils.BrowserSocketRegistry` with
`ktp_controller.api.utils.PubSubBroadcaster` and place it for example
in `ktp_controller.redis`. Naturally, adapt all call sites.

## TODO20

Include `puavo_os_image_name` (str or None) and
`puavo_os_image_release` (str or None) fields in status reports under
`os` object. Contents for these fields are first lines from
`/etc/puavo-image/name` and `/etc/puavo-image/release`,
respectively. Values are `None` if values are not available, for any
reason. status report version must be bumped up to v: 3. Version bump
must be a separate commit, because it's possible that there will be
also other new changes to the status report format. Having a separate
version bump commit makes it easy to re-order commits as needed before
release; the version bump commit must be the last one. Add some unit
tests for the change. Also adapt existing test cases, also in
integration tests, if needed.
