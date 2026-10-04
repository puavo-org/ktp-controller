# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO10

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


## TODO8

WUI: get rid of external htmx (unpkg.com) dependency and vendor it in:
allows us to get rid of unpkg.com in script-src CSP, which must be
updated in this TODO also.


## TODO9

WUI: Add an extra column to Invigilator's student item list: "Allowed
to use browsers" (bool, rendered as simple checkbox). It gets its
value from Abitti2 raw stats message, from `isAllowedToUseBrowser`
field. If it happens that `isAllowedToUseBrowser` does not exist or is
null, then `???` should be rendered instead of
checkbox. `docs/raw_abitti2_stats_message*.json` have examples of raw
Abitti2 stats messages.

When the checkbox is toggled, client must call

`POST
/invigilator/actions/set-exam-session-permission-to-use-browsers`
which accepts data:

```
{
    session_uuid: str,
    allow: bool,
}
```

`allow` is the new value of the checkbox.

`POST
/invigilator/actions/set-exam-session-permission-to-use-browsers` must
require
`invigilator.actions.set-exam-session-permission-to-use-browsers`
permission, which must be granted to `invigilator` role.

`POST
/invigilator/actions/set-exam-session-permission-to-user-browsers` is
still unimplemented and must implemented too in this TODO item. It
must send an async `SET_EXAM_SESSION_PERMISSION_TO_USE_BROWSERS`
request to agent via API POST `/api/v1/system/async_command` endpoint.
