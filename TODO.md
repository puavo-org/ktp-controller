# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO33

## TODO32

WUI, landing page, Host system card.

Add new field: "Free disk space" (en), "Vapaa levytila" (fi). Translate to Swedish.

The value must be one the strings:

(en) "Plenty", "Somewhat", "Small amount", "None" (Please check these and optionally propose better ones, I'm native Finnish speaker)

(fi) "Runsaasti", "Jonkin verran", "Vähän", "Loppunut"

(sv) Add translations.

These four stages must be rendered like so:

Plenty - normal
Somewhat - normal
Small amount - warning
None - error

Use same kind of warning/error rendering as elsewhere.

These values must be calculated from the last status report like so:

status reports have os.stats.disk_usage, if it's missing, then "???" must be displayed and rendered as an error

os.status.disk_usage is available, then stages are calculated like so:

For now, only /home is considered, all other are ignored.

Values must be calculated like so:

None if /home has less than 100M
Small amount if /home has less than 3G
Somewhat if /home has less than 10G
Else Plenty
