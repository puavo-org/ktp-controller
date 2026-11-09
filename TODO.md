# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO41


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
  refuses to do anything until `__work_on_current_exam_package_locked`'s
  `self.__status_report_task.get_last_report()` is not `None`, and
  `__stop_current_exam_package` reads the last status report's student
  list to decide which Abitti2 sessions still need ending, and can mark
  it "expired" on partial failure via
  `self.__status_report_task.mark_expired()`. TODO35 (done; see
  `ktp_controller/agent/tasks/status_report.py`) already moved this
  state behind `StatusReportTask.get_last_report()`/
  `has_last_report_expired()`/`mark_expired()`, so this task should
  read/write it through those accessors from the start rather than a
  private `Agent` field.

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

As with TODO34 (and TODO35, now done), write the actual
commit-by-commit implementation plan once the design questions above
— especially the coalescing-of-heterogeneous-triggers one — are
resolved.
