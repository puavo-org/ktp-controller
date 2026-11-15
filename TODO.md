# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO48

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
