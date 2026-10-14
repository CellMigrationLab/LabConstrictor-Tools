"""`labconstrictor-tools list`: the registered apps, their tools and which hosts may list them (docs/PROTOCOL.md "App hosts").

The listing shows every usable app whatever it declares: the command line is never filtered by `hosts`, which only decides
what Napari, Fiji and QuPath offer.
"""

import argparse
import json

from . import app_hosts, registry


def cmd_list(args: argparse.Namespace) -> int:
    schemas, problems = registry.load_schemas()
    entries = registry.load_entries()[0]
    if args.json:
        hosts = {name: entries[name].get("hosts") for name in schemas if name in entries}
        status = {name: app_hosts.declaration_status(entries[name]) for name in hosts}
        print(
            json.dumps(
                {"apps": schemas, "problems": problems, "hosts": hosts, "hosts_status": status}, indent=2
            )
        )
        return 0
    for name, schema in sorted(schemas.items()):
        print("%s  (%s)" % (name, schema.get("version") or "no version"))
        if name in entries:
            print("    hosts: %s" % app_hosts.declaration_text(entries[name]))
        for tool in schema["tools"]:
            print("    %-24s %s" % (tool["id"], tool["label"]))
    for name, reason in problems:
        print("%s  -- skipped: %s" % (name, reason))
    return 0
