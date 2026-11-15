# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO50

## TODO47

Follow-up cleanups identified while splitting
`ktp_controller/networking/main.py` into `networking/dnsmasq.py` and
`networking/nm.py`:

- The upstream-DNS-server line rendering (`server=/koe.abitti.net/{ip}`
  + `all-servers`) is duplicated between
  `dnsmasq._start_dhcp_dns_server` and `nm._configure_networkmanager`.
  Factor it into a shared helper in `dnsmasq.py` that `nm.py` calls.

- `nm._configure_networkmanager`/`nm._unconfigure_networkmanager` are
  misleadingly named: they manage NetworkManager's internal
  dnsmasq-plugin config file
  (`/etc/NetworkManager/dnsmasq.d/puavo-ers.conf`), not
  NetworkManager's interface/connection state (that's
  `ktp_controller/net.py`'s `Net` class). Rename for clarity, e.g.
  `_configure_nm_dnsmasq_plugin`/`_unconfigure_nm_dnsmasq_plugin`.

- `ktp_controller/networking/main.py`'s four `_command_*` functions
  each hand-roll a nested `try/finally` with a `return` inside
  `finally` (marked `# noqa: B012`) to guarantee cleanup regardless of
  an earlier step's failure. Consider a small shared helper (context
  manager or similar) to express "run these best-effort steps
  regardless of failure" instead of repeating the pattern four times.

- `_command_set_domain` mixes several concerns in one function: CLI
  arg validation, IP resolution via
  `ktp_controller.net.interface_addresses`, dnsmasq hosts-file
  writing, NetworkManager reload, and nginx TLS reverse-proxy
  toggling. Consider decomposing into smaller named steps.

- `ktp_controller/networking/main.py` has an unused `os.path` import
  (pre-existing, unrelated to the dnsmasq/nm split) that can be
  dropped.

## TODO48

Rename the leading-underscore ("private") functions and constants in
`ktp_controller/networking/dnsmasq.py` and `ktp_controller/networking/nm.py`
that are actually accessed from other modules (`main.py` calls into
both; `nm.py` calls into `dnsmasq.py`). A leading underscore signals
"module-private, don't reach in from outside", which is misleading
when the name is in fact part of that module's cross-module API.

Names currently accessed this way (drop the leading underscore, keep
the rest of the name, update all call sites):

- `dnsmasq.py`: `_start_dhcp_dns_server`, `_stop_dhcp_dns_server`,
  `_kill_dnsmasq`, `_DNSMASQ_HOSTS_FILE`, `_LOCAL_DOMAIN`,
  `_KOE_ABITTI_NET_DNS_SERVERS` (all read from `main.py` and/or
  `nm.py`).
- `nm.py`: `_configure_networkmanager`, `_unconfigure_networkmanager`,
  `_reload_networkmanager` (all called from `main.py`).

Names that stay private (no external access, keep the underscore):
`dnsmasq._DNSMASQ_PID_FILE`, `dnsmasq._DNSMASQ_LEASES_FILE`,
`dnsmasq._DNSMASQ_CONF_FILE` (only `_DNSMASQ_CONF_FILE` is reached
into by tests via `monkeypatch`, which is a test-internals concern,
not a cross-module API), `dnsmasq._THIS_NAME`, `nm._NM_CONF_FILE`.

`tests/test_networking_dnsmasq.py` will need its `monkeypatch`/`mocker.patch`
targets and attribute reads updated to match the new names.

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
