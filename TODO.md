# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO25

## TODO23

WUI: Add new card to the landing page: title = Operating system (en),
Käyttöjärjestelmä (fi). Add translation for Swedish.

The card must display a field Release (en), Julkaisu (fi). Add
translation for Swedish. The field displays `os.release` values from
the latest status report.


## TODO24

WUI: include cert expired_at information in Abitti2 card on the
landing page. Display it with appropriate warning highlighting /
markup / icons when there's less than 8 days until the expiration.

There's no existing warning highlight mechanism for cards or card
fields, so this TODO must implement a mechanism for that. There will
be need for warning highlights in future.
