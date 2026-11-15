# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO47

## TODO46

Add new setting (`ktp_controller.settings.Settings`):
`networking_allowed_wan_domains`. It must be a list of valid domain
names (as `validators.domain()` validates).

The default value is a list of following domains:

- dns.msftncsi.com
- www.msftncsi.com
- www.msftconnecttest.com
- ipv6.msftconnecttest.com
- endpoint.security.microsoft.com
- smartscreen-prod.microsoft.com
- smartscreen.microsoft.com
- wdcp.microsoft.com
- wdcpalt.microsoft.com
- wd.microsoft.com
- ctldl.windowsupdate.com
- crl.microsoft.com
- chromeos-staging.abitti.fi
- chromeos.abitti.fi
- register.appattest.apple.com
- m.google.com
- chromeos-ca.gstatic.com
- clients3.google.com
- www.googleapis.com

It's not yet used for anything.

Open questions which needs to be resolved in this TODO: how a list of
strings can be passed via env vars or dotenv files?
