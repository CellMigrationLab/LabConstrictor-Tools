# Three repositories: what goes where

| Repository (suggested name) | Intended publication (**none of these is published yet: install from the git URLs**) | Contains | Depends on |
|---|---|---|---|
| **`LabConstrictor-Tools`** | PyPI `labconstrictor-tools` (import `labconstrictor_tools`) | declaration API (`@tool`, types), schema generation, worker, client, registry, run records, logging, CLI (`check`, `test`, `run`, `register`, `doctor`, `logs`, `support-bundle`, `export-notebook`), notebook form and `%%lc_tool`; the protocol and authoring docs; the example/synthetic apps and the Python test suites | nothing (standard library) |
| **`napari-labconstrictor`** | PyPI + napari hub | the dock widget (`napari_labconstrictor`, `napari.yaml`) and its GUI tests | `labconstrictor-tools`, napari |
| **`LabConstrictor-Fiji`** | Maven artifact `org.cellmigrationlab:labconstrictor-fiji`, Fiji update site "LabConstrictor" | the Java menu command, `LabConstrictor.groovy` (schema -> SciJava dialog -> Appose), the Fiji test harness and cases | `labconstrictor-tools` installed on the machine (found through the registry), Fiji |

The names follow the ecosystems: napari-hub only lists plugins called `napari-*`; Fiji update sites and Maven artifacts are
conventionally lower-case with the product name first.

**Not a fourth repository, but work in existing ones:**
* `LabConstrictor` (the installer/template): add `labconstrictor-tools` to the environment and call
  `labconstrictor-tools register ...` after install / `unregister` before uninstall (docs/LABCONSTRICTOR_INTEGRATION.md).
* Each app (NucleiSky, CellTracksColab, VLab4Mic, ...) owns its `lc_tools.py` declarations next to its code.

**The contract between the three is the schema (`protocol: 1`) and the worker protocol**, nothing else: hosts never import app code
and apps never import hosts. Consequences:
* `labconstrictor-tools` is released first; the hosts declare which protocol versions they speak (`SUPPORTED_PROTOCOLS`) and say so
  in the UI when an app is newer than they are.
* Host CI installs a pinned `labconstrictor-tools` and uses its example app (`labconstrictor_tools.examples.synthetic`, shipped in the package) for end-to-end tests, so no host repository needs the real science packages.
* A protocol change is a major event: bump the integer, keep reading the old one for one release.

**Where the real apps' declarations live.** In each app repository (`lc_tools.py` next to the code, tests in `lc_tests/`).

**Trade-off to know about.** Three repositories means three release processes. While the protocol is still moving, keep release notes of protocol changes in docs/PROTOCOL.md and pin host CI to a released tools version.
