#!/usr/bin/env python3
"""Print the markdown tables of docs/PERF_SHARED_MEMORY.md from benchmarks/results/*.json (median [min-max] seconds).

python benchmarks/shm_table.py benchmarks/results/sandbox_default_128_512.json ...
"""

import json
import sys

COLS = [
    ("export_s", "export"),
    ("load_s", "worker load"),
    ("tool_s", "tool"),
    ("write_s", "worker write"),
    ("result_read_s", "host read result"),
    ("cleanup_s", "cleanup"),
    ("total_s", "TOTAL"),
]


def cell(summary, key):
    if key not in summary:
        return "-"
    s = summary[key]
    return "%.2f [%.2f-%.2f]" % (s["median"], s["min"], s["max"])


for path in sys.argv[1:]:
    data = json.load(open(path))
    env = data["env"]
    print("\n%s  (prewarm=%s, cold cache=%s)\n" % (path.split("/")[-1], env.get("prewarm"), env.get("cold")))
    print("| MiB | tool | path | " + " | ".join(label for _, label in COLS) + " |")
    print("|---|---|---|" + "---|" * len(COLS))
    for mb, tools in data["runs"].items():
        for tool, paths in tools.items():
            for kind, block in paths.items():
                if kind == "cli":
                    s = block["summary"]
                    print(
                        "| %s | %s | cli (cold worker) | %s |"
                        % (
                            mb,
                            tool,
                            "export %s, whole `run` %s" % (cell(s, "export_s"), cell(s, "cli_wall_s")),
                        )
                    )
                    continue
                s = block["summary"]
                print(
                    "| %s | %s | %s | " % (mb, tool, kind)
                    + " | ".join(cell(s, key) for key, _ in COLS)
                    + " |"
                )
