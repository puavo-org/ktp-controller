# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO15

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


## TODO13

WUI: the "End exam" action is the only `wui/actions` endpoint that
doesn't go through the `ktp_controller.messages.Command` /
agent-dispatch path. Every other action
(`set-exam-session-permission-to-use-browsers`,
`change-student-access-code`, `allow-audio-replay`) calls
`ktp_controller.api.client.async_command(...)`, which gets routed to
`ktp_controller.agent.main.Agent` over the API/agent websocket, and the
agent calls `ktp_controller.abitti2.client`. "End exam" instead calls
`ktp_controller.abitti2.client.end_student_exam()` directly from the
WUI/API process (see `_end_student_exam()` and `_post_end_exam()` in
`ktp_controller/wui/actions/routes.py`), bypassing the agent entirely.

This inconsistency should be removed: change "End exam" to use the
same Command/agent dispatch pattern as the other actions.

Required changes (commit bottom-up, same convention as TODO12 used):

1. `ktp_controller/messages.py`: add `Command.END_STUDENT_EXAM`
   and `EndStudentExamCommandData` (fields: `command`, `session_uuid:
   str`, `student_uuid: str` — same shape as
   `SetExamSessionPermissionToUseBrowsersCommandData` minus `allow`).
   Add it to the `CommandData` union and `__all__`. Extend
   `tests/test_messages.py` to match the existing coverage for
   `SetExamSessionPermissionToUseBrowsersCommandData`.

2. `ktp_controller/agent/main.py`: add a dispatch-table entry and a
   `__command_end_student_exam` handler, modeled on
   `__command_set_exam_session_permission_to_use_browsers`, calling
   `ktp_controller.abitti2.client.end_student_exam(session_uuid=...,
   student_uuid=...)` (this function already exists and is already
   used this way from
   `__command_set_exam_session_permission_to_use_browsers`).

3. `ktp_controller/wui/actions/routes.py`: change `_end_student_exam()`
   to call `ktp_controller.api.client.async_command(
   Command.END_STUDENT_EXAM, session_uuid=..., student_uuid=...)`
   instead of calling `ktp_controller.abitti2.client.end_student_exam`
   directly. `_post_end_exam()` itself (route, permission check,
   202-response, background task) stays the same.

4. `tests/test_wui_actions_route.py`: update the existing
   `test_end_exam_*` tests to mock
   `ktp_controller.api.client.async_command` instead of
   `ktp_controller.abitti2.client.end_student_exam`, following the
   same pattern already used for the
   `test_set_exam_session_permission_to_use_browsers_*` tests.

No permission/migration change needed — `wui.actions.end-exam` already
exists and keeps gating the endpoint.


## TODO14

WUI: add three counters to the main invigilator student list view:

1.
"Requires attention" (en)
"Vaatii huomiota" (fi)
Implementer chooses suitable Swedish translation (sv)

2.
"Active" (en)
"Aktiivinen" (fi)
"Aktiv" (sv)

3.
"Finished" (en)
"Päättänyt" (fi)
"Avslutat" (sv)

Each label is followed by a number (0 or greater)

Finished is the total number of students in state Finished

Active is the total number of students in state Active

Requires attention is the total number of students not in state Finished or Active

Counts must be calculated from the whole data, even if there are table
filters. Hence, counts must be also rendered sufficiently apart from
and above the table. Just below the Students h2 and with a bit smaller
font than normally. Moreover, if pico.css has readily availabe style
class for such labeled counts, use it. I'm thinking some kind of small
pills whith color coding: Requires attention is yellow, Active is
green and Finished blue.
