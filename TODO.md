# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO22

## TODO22

Include certificate information in status reports in `abitti2.cert`
field. There's `ktp_controller.schemas._Cert` for that. Fill in the
data from `~/.local/share/digabi/abitti2/certs/cert.pem`. If the file
is not available or cannot be read or is invalid, `abitti2.cert` must
be `None`. `ktp_controller.schemas._Cert.domains` must be a set of
CN + subject alternative DNS names.
