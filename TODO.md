# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO53

## TODO52

API: add endpoint for getting the list of upcoming scheduled exam
packages. Upcoming scheduled exam packages can be locked, but they
don't have to be. Non-locked exam packages are subject to changes
(they can be deleted, modified, etc. by Exam-O-Matic).

Add matching client function which calls the endpoint and returns the
response data.

Then add new card to the landing page of WUI, which displays the first
upcoming scheduled exam package (similar data as the current exam
package card).

Add tests.

