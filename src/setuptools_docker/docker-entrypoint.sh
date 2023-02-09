#!/bin/bash

# usage: process_init_files [file [file [...]]]
#    ie: process_init_files /app/init.d/*
process_init_files() {
	echo
	local f
	for f; do
		case "$f" in
			*.sh)
				if [ -x "$f" ]; then
					echo "$0: running $f"
					"$f"
				else
					echo "$0: sourcing $f"
					. "$f"
				fi
				;;
			*)
        >&2"$0: ignoring $f"
        ;;
		esac
		echo
	done
}

echo "Running entrypoint"
if [ -n "$(ls -A /app/init.d 2>/dev/null)" ]; then
  process_init_files /app/init.d/*
else
  echo "$0: no additional init scripts in /app/init.d found"
fi
exec "$@"
