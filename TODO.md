# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO44

## TODO43

WUI, landing page: add new card: Current exam package. It contains
following fields:

State `ktp_controller.current_exam_package.state`
Scheduled start time: `ktp_controller.current_exam_package.scheduled_start_time`
Started at: `ktp_controller.current_exam_package.started_at`
Scheduled end time: `ktp_controller.current_exam_package.scheduled_end_time`

Scheduled start time must display "in X minutes" if less than 1h
before start, in "X hours" if less than 24h before start, in "X days"
otherwise. If it's past the scheduled start time but the exam package
has not yet started (started_at is None), display "X minutes late", "X
hours late" or "X days late" and highlight the value as an error.
Tooltip must display the exact timestamp.  When started_at is not
None, the value must be the exact timestamp, no tooltip anymore.

Started at must display `-` when it's None. Otherwise, it must display
"X minutes ago", "X hours ago" or "X days ago". Tooltip must display
the exact timestamp.

Scheduled end time must display "in X minutes" if less than 1h
before end, in "X hours" if less than 24h before end, in "X days"
otherwise. If it's past the scheduled end time but the exam package
is still running (state is "running"), display "X minutes ago", "X
hours ago" or "X days ago" and highlight the value as an warning.
Tooltop must display the exact timestamp.

State must display the state. When running overtime, i.e. when state
is "running" but it's past the end time, additional "(overtime)" must
be displayed after the state string and the whole value must be
highlighted as a warning.
