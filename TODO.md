# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO47

## TODO45

ktp_controller/networking/main.py: dnsmasq is now run with no config
file, all options are given as command line args. Change it to use
configuration file instead. The configuration file must be generated
to /var/lib, using same naming pattern as the other files. main.py
must ensure the file is deleted when process exits.

Other than that, the existing functionality must be unchanged.

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
