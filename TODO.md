# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO51


## TODO50

Add ipset capability as `ktp_controller/networking/ipset.py`
module. It must support following features:

- create an ipset, name of ipset and default timeout for
  entries are given as args
- delete ipset by name
- list entries of an ipset
- add entry to the ipset with a timeout
- remove entry from the ipset

Questions which needs to be answered:

- what is the best and most practical way of using ipset from Python?
  - subprocess.check_call / check_output calling `ipset` command?
  - a well maintained Python library?
