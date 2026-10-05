# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO13

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


# TODO12

WUI: student list table must show an additional column (as the second
last column) "Last played audio" (en) / "Den senast lyssnade
inspelningen" (sv) / "Viimeksi kuunneltu äänite" (fi) when
`audioInSomeExam` is true in raw abitti2 stats messages. The cell
value must a be button with label "Allow replaying audio N" (en) /
"Tillåt omspelning av inspelningen N" (sv) / "Salli äänitteen N
uudelleenkuuntelu" where N is the value of `lastAccessedMedia` in raw
Abitti2 stats message.

There are examples of authentic raw Abitti2 stats messages in
docs/raw_abitti2_stat_messsage*.json

So, this TODO effectively requires extending the current
`ktp_controller.wui.invigilator.schemas.StudentListItem` to include
a new field:

- `last_audio`: int | None

  When `audioInSomeExam` is `False`, then `last_audio` of all student
  list items MUST be `None`.
  
  If `last_audio` is `0`, it means that the student hasn't played any
  audio yet.
  
  If `last_audio` is greater than `0`, the value is the identifier of
  the last played audio.7

The context of the student list item template could have
`can_reset_audio`, which is a boolean and `True`, if any of the
`last_audio` fields is an integer. `False` if all of the `last_audio`
fields are `None`.

Which leads to following rendering decisions:

If `can_reset_audio` is `False`, then the column is not shown. If
`can_reset_audio` is `True`, then the column is shown AND if
`last_audio` of student list item is greater than 0, then the cell
must render the button and if `last_audio` is 0, then just empty cell.

The button, when clicked, must display a confirmation overlay, just
like End exam button does. The confirmation overlay must present a
simple question to the user:

```
"Allow student {name} to replay audio {last_audio} in exam {exam_title}?" (en)
"Ska man tillåta examinand {name} att spela upp inspelningen {last_audio} igen i provet {exam_title}?" (sv)
"Sallitaanko kokelaalle {name} äänitteen {last_audio} uudelleenkuuntelu kokeessa {exam_title}?" (fi)
```

Overlay buttons would be:

"Allow" / "Cancel" (en)
"Tillåt" / "Avbryt" (sv)
"Salli" / "Peruuta" (fi)

Clicking Allow must call `POST /actions/allow-audio-replay` which
requires student uuid argument.

Identical pattern with "End exam" action.

ktp_controller.messages requires new command for this.

ktp_controller.agent.main requires handler for the new command. The
handler must finally call
`ktp_controller.abitti2.client.reset_last_audio()`.

Commit in bottom-up order: first commit all low-level changes which
add new capability, but which do not change existing behavrior. Start
from from agent and building the full capability from bottom to up
(WUI front end).
