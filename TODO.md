# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO44

## TODO42

WUI, landing page: Host system info card: add "Started at" field which
displays uptime (mins ago when less than 1h, hours ago when less than
24h, otherwise days ago). The tooltip must display the datetime in
browser local timezone. (Hint. psutil.boot_time() most probably does
not yield datetime with a timezone information, it gives datetime in
the server local timezone, which might be different than the browser
local timezone. The transferred from the server must include timezone
information, otherwise browser cannot display correct datetime). The
value must be highlighted as a warning if uptime is less than 1min or
over 60 days.
