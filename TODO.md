# TODOs

Each item has a unique incrementing id, starting from TODO1, next is
TODO2 and so on. When an item is done, remove it from this document.

When adding new items, always update the following line to define the
ID of the next TODO item.
Next ID: TODO52

## TODO51

Modify ktp_controller/networking/main.py so than when it's called with
"start", it applies following kind of firewall configuration (logic
displayed in Bash code):

```
enable_forwarding() {
  local lan=$1
  local wan=$2
  local ipset_name=$3
  local chain
  local comment
  shift 3

  chain="$ipset_name"
  comment="$ipset_name"

  require_interface "$wan"
  require_interface "$lan"
  [[ "$wan" != "$lan" ]] || die "WAN and LAN interface must be different"

  log "recreating filter chain '$chain'"
  remove_rules_by_comment nat POSTROUTING "$comment"
  remove_rules_by_comment filter FORWARD "$comment"
  recreate_chain filter "$chain"

  # Log new allowlisted flows (rate-limited to avoid log flooding)
  add_rule filter "$chain" \
    --match conntrack --ctstate NEW \
    --match set --match-set "$ipset_name" dst \
    --match limit --limit 30/second --limit-burst 100 \
    --jump LOG --log-prefix "$ipset_name " --log-level 6

  # Allow only ipset allowlisted destinations
  add_rule filter "$chain" \
    --match set --match-set "$ipset_name" dst \
    --jump ACCEPT

  # Drop everything else
  add_rule filter "$chain" --jump DROP

  # Allow return traffic for established connections
  add_rule filter FORWARD \
    --in-interface "$wan" --out-interface "$lan" \
    --match comment --comment "$comment" \
    --match conntrack --ctstate RELATED,ESTABLISHED \
    --jump ACCEPT

  # Enforce allowlist for new LAN->WAN traffic
  add_rule filter FORWARD \
    --in-interface "$lan" --out-interface "$wan" \
    --match comment --comment "$comment" \
    --jump "$chain"

  # NAT only for allowlisted destinations
  add_rule nat POSTROUTING \
    --out-interface "$wan" \
    --match comment --comment "$comment" \
    --match set --match-set "$ipset_name" dst \
    --jump MASQUERADE

  log "internet forwarding enabled: LAN '$lan' -> WAN '$wan'"
}
```

And when called with "stop", it removes firewall rules like so:

```
disable_forwarding() {
  local ipset_name=$1
  local chain
  local comment
  shift 1

  chain="$ipset_name"
  comment="$ipset_name"
  log "removing forwarding rules"
  remove_rules_by_comment nat POSTROUTING "$comment"
  remove_rules_by_comment filter FORWARD "$comment"
  flush_and_delete_chain filter "$chain"
}
```
