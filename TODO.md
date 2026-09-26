# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO6

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

## TODO4

WUI: Show simple and elegant "connection lost (a bit more descriptive
short text instead, I just couldn't come up with something
immediately)" overlay on all invigilator index page when the websocket
connection is lost. The overlay should be somewhat transparent to give
the user a hint that there's more to the page but it's temporarily
unavailable.

## TODO5

WUI: hx-confirm on end-exam button action seems very sluggish and is
quite ugly also. Replace it with: "when end-exam button is clicked,
render a text: 'Really end exam?' and two buttons Yes and No in the
same cell.
