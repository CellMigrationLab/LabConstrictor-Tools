# Tools 0.3.0-alpha.1 (alpha: for the first human tests)

Pre-release `v0.3.0-alpha.1`, Python version `0.3.0a1`. Tick "pre-release" when you create the GitHub release. This is for the first human tests ([HUMAN_TEST_PROTOCOL.md](HUMAN_TEST_PROTOCOL.md)); it is not a stable release, and apps pin it only for a human-test round.

Install: `python -m pip install https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/v0.3.0-alpha.1.zip`

## Why a new number

`v0.2.0-rc.1`, `v0.2.0-rc.2` and `main` all reported version `0.2.0rc1` and the same `features` (`reserved_inputs_v1`, `retention_prune`) although their code differs, so a host could not tell them apart. `0.3.0a1` and the new feature id `shm_order_v1` make this build recognisable. Order: `0.2.0rc1 < 0.3.0a1 < 0.3.0`. There will be no `rc.3`.

## Changes since v0.2.0-rc.2

* **Worker exit code 3 (#124).** The hint "an import failed" is shown only when the worker said so on stderr (the marker); exit code 3 alone no longer is called an import failure.
* **Shared-memory `order` (#125).** A shared-memory image descriptor's `order` is honoured for `C` / `C_ORDER` and `F` / `F_ORDER` (the tool always gets a C-ordered copy of the same logical image); any other value is refused with `unreadable_image` instead of silently giving a transposed image. Feature id `shm_order_v1` (the behaviour came with #125; the id is added now).
* **Big TIFFs are memory-mapped.** TIFF files of 8 MiB or more that are uncompressed and contiguous are opened as a copy-on-write memory map (faster, less memory; the file is never changed). `LC_TIFF_MEMMAP=0` reads them the plain way. No feature id: it is an optimisation with no behavioural contract.
  * **Windows caveat.** A tool that keeps a reference to its input (a global variable, a stored exception, a lingering thread) keeps the file locked on Windows until the worker ends; the host cannot delete or overwrite that file in the meantime. Linux and macOS are not affected.
* **Run records (in the code of rc.2, first number that lists them).** `runs.build_record`, `runs.record_json` and `runs.done_status` exist from 0.3.0a1. A host checks `min_tools_version` 0.3.0a1 or `hasattr(runs, "build_record")`. No feature id.
* **CI and testing only (#126, #127).** `smoke_migration` accepts template 0.1.17 and can test a top-level Tools import; a dispatch-only release sandbox workflow tests a released app on fresh Linux, macOS and Windows runners. Nothing changes for users.
* **Version and features.** `__version__` is `0.3.0a1`; `features` is `reserved_inputs_v1`, `retention_prune`, `shm_order_v1`. `tests/fixtures/schemas/tools_0.3.schema.json` and `compat.version_order` know the new number.

## For hosts

* Require `min_tools_version` `0.3.0a1` when you use `runs.build_record` / `record_json` / `done_status`, and the feature `shm_order_v1` when you send `F`-ordered shared-memory blocks ([PROTOCOL.md](PROTOCOL.md#tools-version-and-features)).
* Pre-release pinning rules and the tag/version name rule (`-alpha.N` <-> `aN`, `-rc.N` <-> `rcN`): [OPERATIONS.md](OPERATIONS.md#releases-and-tags).
