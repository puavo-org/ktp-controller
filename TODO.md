# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO32

## TODO28

WUI: render a blueish (color wich pico.css already provides and which
works in both light and dark themes) dashed underline on all texts
wich have tooltips.

## TODO30

WUI: Display "Page refreshed N seconds ago". This text must itself get
refreshed (once every ~5secs, starting at 00, then 05, etc.) solely by
the browser and independently of WUI backend, websockets, whatnot. N
is the number of seconds since the last request (no matter what data
the response actually brought in). It's main purpose is to the give
the end user reliable information about the last time any data got
updated in the browser view. If there are better ways to display or
obtain this information, let me know.

## TODO31

WUI, landing page: In the "Controller info" card there's "Started at"
field. Instead of displaying an exact timestamp, display a time
relative to the current time, like so:

If "Started at" is less than 1m ago, display "1 second ago / N seconds ago".
If "Started at" is less than 1h ago, display "1 minute ago / N minutes ago".
If "Started at" is less than 24h ago, display "1 hour ago / N hours ago".
Otherwise display "1 day ago / N days ago".

The relative time difference must be calculated on the browser,
independently from the backend to give the end user reliable timing
information. Just like TODO29.

In addition, if "Started at" is less than 1 minute ago, highlight the
value as a warning.

Display the exact started_at timestamp as a tooltip.
