# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO58


## TODO56

WUI: look at all JavaScript files. Identify refactoring opportunities.


## TODO57

WUI: ktp_controller/wui/students.py parses Abitti2's raw-stats
`updateTime`/`examFinishedAt` timestamps with a bare `.astimezone()`,
which converts to the server process's local system timezone instead
of UTC. Every other timestamp in the system is stored/handled as UTC.
Parse these as UTC-aware datetimes instead (e.g.
`.astimezone(datetime.timezone.utc)` or equivalent), for consistency.
