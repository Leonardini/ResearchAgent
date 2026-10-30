#!/bin/sh
# Fails unless every skill's copy of a shared reference is a link to the one file in shared/.
# A separate copy would let the skills drift apart silently.
here=$(cd "$(dirname "$0")" && pwd)
status=0
for f in ai-tells.md plain-strong-writing.md; do
  for skill in "$HOME/.claude/skills/humanizer" "$here/../scientific-humanizer"; do
    p="$skill/references/$f"
    if [ ! -L "$p" ] || [ "$(cd "$(dirname "$p")" && realpath "$(readlink "$p")")" != "$here/$f" ]; then
      echo "NOT SHARED: $p is not a link to $here/$f"; status=1
    fi
  done
done
[ $status -eq 0 ] && echo "shared references OK"
exit $status
