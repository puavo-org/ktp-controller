# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO36


## TODO35

Move the "create status reports" task out of `Agent`
(`ktp_controller/agent/main.py`) into `ktp_controller/agent/tasks/`,
following the pattern established for "refresh exams" (see
`ktp_controller/agent/tasks/base.py` and
`ktp_controller/agent/tasks/refresh_exams.py`). Reuse `task_guard()`
and `periodic()`-style helpers from `tasks/base.py` where they fit.

This task is structurally harder than refresh-exams and needs its own
design, not a copy-paste of `RefreshExamsTask`:

- **Many more trigger sites, all fire-and-forget.** Today,
  `self.__status_report_should_be_created` (an `asyncio.Event`) is set
  from 6 places: `__set_auto_control` (enable/disable auto-control
  commands), `__command_create_status_report`, the exam-package state
  machine (`__work_on_current_exam_package`, after any state change),
  and three Abitti2 message handlers
  (`__handle_abitti2_security_code_message`,
  `__handle_abitti2_stats_message`, `__handle_abitti2_exams_message`).
  None of these callers wait for the report to actually be built —
  unlike refresh-exams' `REFRESH_EXAM_INFO` command, nobody needs a
  per-call result. So the right primitive here is not
  `CoalescingQueue` (which hands back a per-request result) but a
  simpler "mark dirty, build at most once more" signal — essentially
  what the existing `asyncio.Event` + `asyncio.wait_for(..., timeout=...)`
  loop in `__create_status_reports_task` already does. Consider adding
  a small `DirtySignal` (or similar) primitive to `tasks/base.py` that
  wraps this pattern generically (`mark_dirty()`,
  `await wait_dirty_or_timeout(seconds)`), or conclude a bare
  `asyncio.Event` is simple enough as-is and not worth abstracting
  further — decide this as part of the design, don't force a queue
  where one doesn't fit.

- **The produced report is read back by other `Agent` logic, not just
  sent off.** `__create_status_report()` stores its result in
  `self.__last_status_report` / `self.__has_last_status_report_expired`
  / `self.__last_status_report_sent_to_examomatic_at`. Unlike
  refresh-exams, these aren't private to the task — the exam-package
  state machine reads `__last_status_report` directly in
  `__work_on_current_exam_package_locked` (to gate all transitions on
  "do we have a complete view of the system yet") and in
  `__stop_current_exam_package` (to check which students still have
  active sessions, and to mark the cached report "expired" after a
  failed end-student-exam attempt). Any extraction must keep this data
  visible to that code — e.g. the new task object becomes the single
  owner of "last report" state and exposes small accessor methods
  (`get_last_report()`, `mark_expired()`) that `Agent` calls instead of
  touching its own fields directly, rather than trying to make the
  task's output opaque/private the way refresh-exams' was.

- **Report assembly reads a large, scattered slice of `Agent` state.**
  `__create_status_report()` pulls from ~10+ `Agent`-private caches and
  methods (`__last_received_security_code`, `__last_received_students`,
  `__last_received_answer_count`, `__last_message_from_abitti2_received_at`,
  `__get_exam_stats()`, `__get_stats()`, `__get_abitti2_version()`,
  `__is_auto_control_enabled`, `__started_at`, OS/image info, etc.),
  all populated by code elsewhere in `Agent` that is out of scope for
  this move (Abitti2 message handling, connection/stats tracking).
  Rather than giving the new task module direct access to `Agent`
  internals, define a typed snapshot (e.g. a `StatusReportInputs`
  dataclass) that `Agent` assembles fresh each time from its own state
  and hands to a free function (e.g.
  `build_status_report(inputs: StatusReportInputs) -> dict`) in the new
  task module. This keeps the new module ignorant of `Agent` and
  independently unit-testable, same as `_refresh_exams()` is today.

- What can move essentially as-is: the "should we also send this
  report to Exam-O-Matic now" rate-limiting logic
  (`__get_seconds_until_time_to_send_next_status_report_to_examomatic`)
  and the send-to-Exam-O-Matic / save-to-API calls at the end of
  `__create_status_report()`.

- Trigger plumbing at the 6 call sites listed above becomes a one-line
  swap to `self.__status_report_task.mark_dirty()` (or whatever the
  chosen signal's API ends up being called).

As with TODO34/refresh-exams, write the actual commit-by-commit
implementation plan (capability commits for the new module, mechanical
move of state ownership, final connecting commit, tests) once the
design above is settled — this entry only captures the problem shape
and the key design decisions still open.
