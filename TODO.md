# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO60


## TODO58

WUI: Current scheduled exam package card shows Started at timestamp in
UTC timezone. It must be changed to display it in browser-local
timezone instead and to display the timezone offset too, just like
tooltips.


## TODO59

Networking/dnsmasq: currently dnsmasq uses three upstream servers:
9.9.9.9, 8.8.8.8 and 1.1.1.1 to resolve koe.abitti.net addresses. In
addition, I want to append the hosts's default nameserver (if there's
one defined) to the list.

This item Closes #68, add that to the final connecting commit.
