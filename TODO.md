# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO38


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


## TODO36

Move the exam-package state machine
(`Agent.__work_on_current_exam_package`/`__work_on_current_exam_package_locked`
in `ktp_controller/agent/main.py`) into `ktp_controller/agent/tasks/`,
following the "refresh exams" precedent (TODO34, already done; see
`ktp_controller/agent/tasks/refresh_exams.py`) and reusing
`task_guard()` from `tasks/base.py`.

This was flagged in the original refresh-exams plan as the best
candidate to validate that `CoalescingQueue` actually generalizes
beyond a single trivial payload type, because unlike refresh-exams it
has a *meaningful* payload (a `Trigger` value) and more trigger
sources. Doing this one is likely to reveal that `CoalescingQueue` as
built doesn't fit as-is — the issues below need to be resolved before
writing an implementation plan, not papered over:

- **Today's triggers**: one periodic-ish `TIME` trigger (fired from
  every API ping/pong round-trip in `__communicate_with_api`, so
  roughly every `approx_api_ping_interval_sec`) and four manual
  triggers from API commands — `PREPARE_CURRENT_EXAM_PACKAGE`,
  `START_CURRENT_EXAM_PACKAGE`, `STOP_CURRENT_EXAM_PACKAGE`,
  `ARCHIVE_CURRENT_EXAM_PACKAGE` — all routed through
  `__command_change_current_exam_package_state`. Unlike the
  status-reports task (TODO35), manual-trigger callers here *do* need
  a per-call result: `changed: bool` to pick `OK` vs `OK_NO_CHANGE`,
  or the caught exception's message to return `ERROR`. So this is
  closer to refresh-exams' request/response shape than to TODO35's
  fire-and-forget one — `CoalescingQueue[Trigger, bool]` looks right
  on the surface.

- **The real problem: coalesced payloads aren't interchangeable.**
  Refresh-exams' payload (`is_spontaneous: bool`) only affects logging
  — any run equally satisfies any coalesced requester. Here, a
  `Trigger` selects which state transition is attempted (e.g.
  `MANUAL_START` is only valid from `"ready"`, `MANUAL_STOP` only from
  `"running"`). If a `MANUAL_START` and a `MANUAL_STOP` request happen
  to land in the same coalesced batch, running the body "once for the
  batch" doesn't have an obvious correct meaning, and it's unclear what
  `changed` result either caller should get back. This needs an actual
  design decision, e.g.:
  - Only ever coalesce `TIME` triggers with each other (cheap, already
    idempotent, matches today's "drop if busy" behavior); run every
    manual trigger as its own un-coalesced request, processed in
    arrival order — i.e. two different queues/paths feeding one
    consumer, not one homogeneous `CoalescingQueue`.
  - Or: reject/fail fast a manual request that would otherwise merge
    with an incompatible already-pending one, rather than silently
    running "something".
  - Explicitly out: silently picking one trigger from a mixed batch and
    reporting its `changed` result to every caller, regardless of what
    they actually asked for.

- **Today's `TIME` trigger is drop-on-busy, not coalesce-on-busy**:
  `__work_on_current_exam_package` skips entirely (returns `False`
  without ever acquiring the lock) if the lock is already held and the
  trigger is `TIME`. `CoalescingQueue` has no "drop" mode, only
  "merge into the one pending batch" — decide whether moving to
  coalesce-instead-of-drop for `TIME` is an acceptable (probably
  harmless, arguably better) behavior change, and say so explicitly
  rather than assuming it.

- **State read from the status-reports task**: the state machine
  refuses to do anything until `__last_status_report is not None`
  (`__work_on_current_exam_package_locked`), and
  `__stop_current_exam_package` reads the last status report's student
  list to decide which Abitti2 sessions still need ending, and can mark
  it "expired" on partial failure. This is the same
  `__last_status_report`/`__has_last_status_report_expired` state
  TODO35 is about relocating — sequence TODO36 after TODO35 (or at
  least design them together), so this task reads/writes that state
  through whatever accessor TODO35 ends up exposing instead of a
  private `Agent` field that's about to move out from under it.

- **Owns a nested dynamic task**: entering/leaving the `"running"`
  state starts/stops a second background task
  (`self.__nonfinal_answers_download_task`, managed by
  `__ensure_nonfinal_answers_download_task_is_running`/
  `__stop_nonfinal_answers_download_task`). This lifecycle is tightly
  coupled to the state machine (only meaningful while "running") and
  should move together with it rather than being left behind in
  `Agent`.

- **Testbed crash hook**: `__command_crash` (the `CRASH_AGENT` test-only
  command) just sets `self.__do_crash = True`; the actual
  `sys.exit(1)` happens on the *next* state-machine tick, inside
  `__work_on_current_exam_package_locked`. Keep this working (or
  replace it with something equivalent) when moving the body out —
  don't lose the deferred-crash behavior testbed tests may rely on.

- Other state read during transitions
  (`ktp_controller.api.client.get_locked_exam_packages`,
  `__is_auto_control_enabled`, `__last_received_exam_list`,
  `__last_cold_reset_time`, Abitti2 reset/session calls) should follow
  the same "typed inputs snapshot assembled by `Agent`, pure function
  in the new module" shape proposed for TODO35, rather than giving the
  new module direct access to `Agent` internals.

As with TODO34/TODO35, write the actual commit-by-commit
implementation plan once the design questions above — especially the
coalescing-of-heterogeneous-triggers one — are resolved.


## TODO37

Move the "answers file upload" task
(`Agent.__upload_answers_files`/`__answers_file_upload_task` in
`ktp_controller/agent/main.py`) into `ktp_controller/agent/tasks/`,
reusing `periodic()` from `tasks/base.py` (already built for exactly
this shape of task, see TODO34).

Unlike TODO35/TODO36, this one is simple and shouldn't need any new
design:

- **No command trigger, no coalescing needed.** It only has one
  trigger — the periodic loop itself, every 30 seconds
  (`__answers_file_upload_task`) — so this is a direct fit for the
  existing `periodic()` helper, not `CoalescingQueue`. No new
  primitive is needed.

- **Already a free function in disguise.** `__upload_answers_files`
  doesn't read or write any `Agent` state at all: it lists
  `ktp_controller.files.ANSWERS_FILE_DIR`, picks the latest `*.meb`
  file not yet uploaded, and calls
  `ktp_controller.agent.answers.upload_answers_file()` (already a
  standalone function in `ktp_controller/agent/answers.py`, taking no
  `Agent` reference). It can move to a new
  `ktp_controller/agent/tasks/answers_upload.py` essentially verbatim,
  as a plain `async def upload_one_pending_answers_file() -> None`
  function — no inputs-snapshot dataclass or task-owned state needed,
  unlike TODO35/TODO36.

- **Wiring**: `Agent.forever()` replaces
  `tg.create_task(self.__answers_file_upload_task())` with something
  like
  `tg.create_task(base.periodic("answers file upload", 30, upload_one_pending_answers_file, on_error_message="answers file upload failed"))`
  directly — there's likely no need for a dedicated task *class* here
  at all (contrast with `RefreshExamsTask`, which needed one to own
  its `CoalescingQueue`).

- **Tests**: add `tests/test_agent_tasks_answers_upload.py` mirroring
  `tests/test_agent_tasks_refresh_exams.py`'s style, exercising the
  moved function directly (mock
  `ktp_controller.agent.answers.upload_answers_file`, assert it's
  called with the latest `.meb` file and that the loop stops after the
  first successful upload per call).

This is a good one to do right after TODO35/TODO36's harder design
work is settled, as a low-risk exercise of the same move pattern
(capability commit → final connecting commit → tests), and to confirm
`periodic()` itself needs no changes before `__file_cleanup_task`/
`__old_exam_info_cleanup_task` get the same treatment later.
