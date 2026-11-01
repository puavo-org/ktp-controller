# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO30

## TODO28

WUI: render a blueish dashed underline on all texts wich have
tooltips.


## TODO29

WUI: the invigilator-path live-update websocket mechanism
(`ktp_controller/wui/invigilator/routes.py`'s `/invigilator/ws` route,
`ktp_controller/wui/utils.py`'s `BrowserSocketRegistry`/
`raw_abitti2_stats_message_listener`, and
`ktp_controller/wui/static/status_updates.js`) already serves pages
outside `/invigilator/` (the landing page's student-count pills). Move
it out of the invigilator-specific path into a shared location, and
use it to make the nav bar's severity icon (added for the previous
TODO27) update live instead of only at page load.

