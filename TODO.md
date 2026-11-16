# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO50

## TODO49

Drop the redundant module-name prefix from constant names in
`ktp_controller/networking/dnsmasq.py` and
`ktp_controller/networking/nm.py`. Each module is already named after
the thing it configures, so repeating that name inside its own
constants adds nothing:

- `dnsmasq.py`:
  - `_DNSMASQ_PID_FILE` -> `_PID_FILE`
  - `_DNSMASQ_LEASES_FILE` -> `_LEASES_FILE`
  - `_DNSMASQ_HOSTS_FILE` -> `_HOSTS_FILE`
  - `_DNSMASQ_CONF_FILE` -> `_CONF_FILE`
- `nm.py`:
  - `_NM_CONF_FILE` -> `_CONF_FILE`

Update all call sites in `dnsmasq.py`/`nm.py` themselves, references
from `main.py` (whichever of these are still accessed with a leading
underscore at the time vs. renamed per TODO48), and the
`monkeypatch`/attribute-read targets in
`tests/test_networking_dnsmasq.py`.
