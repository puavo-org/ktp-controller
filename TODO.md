# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO8

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


## TODO7

Add a subpage to WUI's Invigilator's view (`GET
/invigilator/student_access_code`) which renders the following:

- the current student access code of Abitti2 (it's available in
  Abitti2 raw status messages) in big and clear font. It must be
  updated when `abitti2_stats_changed` message is received via
  websocket.

- a button for sending an async `CHANGE_STUDENT_ACCESS_CODE` request
  to agent via API POST `/api/v1/system/async_command` endpoint. The
  button must call `POST
  /invigilator/actions/change-student-access-code`, which in turn must
  send the the actual async request to API. `POST
  /invigilator/actions/change-student-access-code` must require
  `wui.invigilator.change-student-access-code` permission which must
  be granted to `invigilator` role.

`GET /invigilator/student_access_code` must require
`wui.invigilator.view` permission, which must be granted to
`invigilator` role.

This new subpage must react to lost connection just like the main
Invigilator's view does. If this needs refactoring and moving common
code a better place, do it but in a separate commits any other
changes.
