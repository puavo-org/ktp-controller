# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO35


## TODO34

ktp_controller/agent/main.py is too big. I want to split logic to
clearly interfaced smaller modules.

One obvious way of splitting the logic is to move *tasks* (at least
most of them) to dedicated modules and define clear queue-based
(producer/consumer) interace between `Agent` and new task modules or
classes.

Make a plan for such move.

- Identify common generic task-related logic which could be moved to a
  task lib.

- Use "refresh exams" task as the first example of how to move tasks
  out from `ktp_controller/agent/main`. The "refresh exams" task
  should be capabale of receiving "refresh exams" requests from a
  queue and then executing them asynchronously. There's no point of
  having more than 1 pending "refresh exams" request
  simultaenously. There are two different kind of triggers/sources for
  these requests: periodic and commands received from API.

New tasks should be placed to `ktp_controller/agents/tasks/` package.

Note that there are many other similar kind of task ready to get moved
once the new structure is solid and generic enough.
