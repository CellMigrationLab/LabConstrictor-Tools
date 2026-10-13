# Shared memory for big images: measurements, feasibility per host, recommendation (issue #66)

Status: research result, nothing here is implemented. Written 2026-10-13 against Tools `main` (0f97d65). The scripts that produced every number are in [`benchmarks/`](../benchmarks) and the raw results in `benchmarks/results/`.

## 1. Answer first

**Recommendation: do it for Fiji only, as an opt-in input transport with a size threshold (about 256 MiB), after a small Tools change. Do not do it for Napari or QuPath now. Do not add shared-memory results (outputs) yet.** The expected gain is modest (about 0.5 s per 512 MiB on Fiji at the median, more when the machine or disk is under stress), so this is a medium-low priority feature, never to be on by default until it is measured on real Windows and macOS hardware.

Why, in five lines (details and caveats below):

1. **Transport is not the cost.** A warm task round trip adds 2 to 5 ms (`transport_s`, JSON and pipes) and the JSON line carrying a descriptor is about 150 bytes. Everything that costs time is moving pixels: allocating and touching fresh memory, writing and reading the TIFF.
2. **Against a warm page cache the TIFF path is as fast as shared memory on a Python host.** At 512 MiB the median end to end difference between the two is under 0.1 s in the sandbox ("prewarmed" rows), because `tifffile` writes and reads at memory speed and the shared path needs the same number of fresh 512 MiB buffers (section 4.3). Shared memory mostly removes variance (writeback stalls, 512 MiB of block I/O) and the disk, not a copy.
3. **Fiji is where it pays.** Fiji's own TIFF encoder and reader (`ij.io.FileSaver`, `Opener`) cost 0.83 s write and 0.78 s read per 512 MiB at the median (range 0.39 to 2.75 s), against 0.32 s to fill and 0.38 s to read back a block, with the Appose class Fiji already ships and a Java 8 compatible build. A real Java to Python proof passes (section 5.2).
4. **Napari gains nothing on input** (`tifffile.imwrite` 0.14 s versus 0.18 to 0.40 s to fill a block). Its only real gain is showing a result without a second copy, which needs care (section 5.1). **QuPath** exports at most 100 megapixels per plane from a slide whose decode time dominates, converts a `BufferedImage` before any block exists, and has no guaranteed JNA (section 5.3).
5. **Shared memory raises the hard memory floor.** A block cannot be evicted like page cache. At 1 GiB the shared round trip was killed by the kernel OOM killer in the 16 GB sandbox, where the TIFF round trip finished (section 4.4).

A cheaper change helps every host and needs no protocol work: let the worker memory-map an uncompressed TIFF read-only/copy-on-write (`tifffile.memmap`, the plan's performance idea 3). Load goes from 0.19 s to 0.04 s at 512 MiB (warm) and from 0.58 s to 0.24 s (cold), and no private copy is made (section 4.5). It is a Tools-only change and should be tried before, or together with, shared memory.

## 2. What exists today (read from the code)

* **Input.** `convert._read_image` accepts a TIFF path or an Appose-shaped descriptor `{"appose_type": "ndarray", "shm": {"name"}, "shape", "dtype"}`. `_ndarray_from_shared_memory` attaches (`track=False` on Python 3.13, a patched `resource_tracker.register` before that, so the worker never unlinks the host's block), builds `np.ndarray(shape, dtype, buffer=shm.buf)`, **copies** it (`view.copy()`) and closes. That is one fresh array in the worker. It validates name, dtype kind and that the block is large enough. It **ignores any `order` key** (an `F_ORDER` descriptor would silently be read as C order, i.e. transposed: see section 6).
* **Output.** `build_results` always writes images as `<name>.tif` with `tifffile.imwrite` into the host-owned `_job_dir`; `np.asarray` and `portable_dtype` do not copy for uint8/uint16/float32 (they copy for bool, float64 and wide integers, with temporaries).
* **Hosts.** Napari writes `export_layer` TIFFs with `tifffile` and reads results back with `tifffile.imread` (the array becomes the layer data). Fiji drives the worker through the Appose Java `Service` and saves images with `FileSaver.saveAsTiff`, results come back through `IJ.openImage`. QuPath has its own Groovy JSON-lines client (`LcWorker`, `ProcessBuilder`), no Appose, and exports with `ImageWriterTools.writeImageRegion`.
* **Tests.** `tests/test_roundtrip_shared_memory.py` covers ownership (the worker leaves the block alone).

## 3. Method, and what the sandbox cannot represent

`benchmarks/shm_bench.py` plays the host (an in-memory uint16 array, as a Napari layer or an ImageJ plane) against a **real worker** (`python -m labconstrictor_tools serve --module shm_bench_app`, warm, one process for all runs) and times each phase with `perf_counter`. The worker's own phases (`load_inputs_s`, `tool_s`, `write_results_s`) are the `timings` field of `COMPLETION`. Tools are in `benchmarks/shm_bench_app.py`: `image_max` (reads the image once, tiny result: input transport only), `invert` (one new array, a TIFF result: the full round trip), `passthrough`, and two prototypes that are not in the protocol (`invert_to_shm`: result returned as a block; `view_max`: borrowed read-only view, no worker copy). The real command line (`labconstrictor-tools run`, a new worker per call) is timed with `--cli`. Each cell is **median [min-max] of 3 runs**, uint16 square images of 128, 512 and 1024 MiB.

Two modes are reported because the sandbox has a property a laptop does not:

* **default**: the sandbox as it is.
* **prewarm**: before each export, task and read, the driver touches and frees K x image size of memory (not timed). On this micro-VM that makes the guest reuse pages the hypervisor already backs, which is closer to bare hardware.

**What this sandbox cannot represent. Read this before using any absolute number.**

* It is a Firecracker-style micro-VM, 4 cores, 16 GB, no swap, about 8.5 GB of it already held in tmpfs by another tenant (so about 6 GB usable), a virtual disk, Python 3.11. **First touch of memory the hypervisor has not backed costs 1 to 3 s per 512 MiB** (system time), against 0.1 s when it has (section 4.2). This single effect explains the large spreads and the "unexplained" times, and it is not what a user's machine does.
* The disk is not slow for reads here (a 512 MiB cold-cache read took 0.34 s), and writes mostly land in page cache. A real slow disk, a network home directory, an HDD, antivirus scanning of temporary files (Windows Defender) and cloud-sync folders are **not** represented. Those are exactly the cases where shared memory would win more.
* No GPU, no real host applications (no Fiji, QuPath or Napari were run; the host side is modelled by a Python process and by the Java snippets), Linux only: **Windows and macOS behaviour below is from documentation and code reading, not measured.**
* THP is `madvise` here, so numpy arrays use huge pages and show few page faults; Windows and macOS differ.

## 4. Results

### 4.1 End to end (host export, worker, result read, cleanup), seconds

`image_max` = input transport only (Napari-like host, tifffile). `invert` = full round trip, result as TIFF. Disk path = TIFF in a scratch folder on the sandbox disk; shm = `SharedMemory` block. Export does not wait for the disk (no fsync) in the "export" column, as a host would not. Full tables: `python benchmarks/shm_table.py benchmarks/results/*.json`.

| MiB | tool | mode | disk path total | shared-memory total |
|---|---|---|---|---|
| 128 | image_max | default | 0.20 [0.18-1.36] | 0.20 [0.19-0.22] |
| 128 | invert | default | 0.36 [0.32-1.61] | 0.34 [0.33-0.76] |
| 512 | image_max | default | 1.91 [0.69-6.03] | 1.30 [0.83-2.45] |
| 512 | image_max | prewarm | 0.64 [0.61-0.78] | 0.75 [0.75-1.50] |
| 512 | image_max | cold page cache (prewarm) | 0.96 [0.58-0.98] | 0.90 [0.78-0.91] |
| 512 | invert | default | 5.95 [1.39-7.30] | 1.33 [1.25-4.72] |
| 512 | invert | prewarm | 1.95 [1.86-3.79] | 1.71 [1.65-4.12] |
| 1024 | image_max | default | 3.53 [1.74-15.33] | 3.01 [2.69-3.02] |
| 1024 | image_max | prewarm | 2.55 [1.97-3.56] | 1.61 [1.58-1.91] |
| 1024 | invert | default (3 runs) | 15.29, 6.46, 3.94 | killed by the OOM killer (worker exit -9) |
| 1024 | passthrough | default, results in tmpfs | 1.90 [1.73-12.70] | 4.14 [3.76-6.02] |

Per phase at 512 MiB, `invert`, prewarm mode, medians: disk path export 0.14, worker load 0.18, tool 0.17, worker write 0.99, host read 0.16, cleanup 0.31; shared path export 0.42, load 0.25, tool 0.53, write 0.13, read 0.19, cleanup 0.12. The task round trip outside the worker's own timings (`transport_s`: pipes, JSON, scheduling) is **0.00 to 0.01 s in every row**, including at 1 GiB. The real CLI (`run`, cold worker) takes 0.37 s at 128 MiB and 0.52 s at 512 MiB for `image_max`, about 0.15 to 0.2 s of which is interpreter start.

Reading the table honestly: the sandbox gives shared memory a clear lead only in "default" mode, where it is mostly avoiding an erratic disk path, and no lead at all in "prewarm" mode for a Python host. At 1 GiB `passthrough` shows the shared path worse (the worker's TIFF write after two fresh gigabytes stalled). None of this is a stable speed-up measurement; it is evidence that the gain is small and conditional.

The two things shared memory does remove, from the kernel counters in the JSON (`k_nr_written`): **512 MiB of block I/O per input** (131073 pages written for the TIFF, 0 for the block), and the erratic part of the disk path's spread.

### 4.2 The "unexplained" numbers of the plan are explained

| Plan figure | Reproduced here | Cause |
|---|---|---|
| TIFF read 3.7 s per 512 MiB | `image_max` disk, run 1: worker load 3.28 s; warm 0.19 s; cold-cache read of the same file 0.34 s | not the file: **first touch of fresh memory** for the destination array (system time), hypervisor backing |
| host TIFF write 3 s per 512 MiB | export 3.41 s in run 1, Java `FileSaver` 2.4 to 2.8 s in the first run, 0.14 s warm (tifffile), 0.39 to 0.83 s (ImageJ) | page backing of the page-cache pages plus dirty-page throttling |
| shm conversion 0.44 s per 512 MiB | 0.21 to 0.28 s warm, up to 1.9 s when memory is cold | one copy: 0.065 s of memcpy plus about 0.15 s of page faults, or 1 to 3 s of hypervisor backing |
| 2.4 s in the worker for a 512 MiB shared-memory task | **reproduced exactly**: `invert`, shm, run 3: load 1.09 + tool 0.18 + write 1.15 = 2.42 s | the conversion is only the first of **three** steps that each allocate or fill fresh 512 MiB (input copy, the tool's output array, the TIFF write); each costs 0.1 to 0.2 s when memory is backed and 1 to 3 s when it is not |
| 15 s for 1 GiB | **reproduced**: 15.29 s total for `invert` 1 GiB, run 1 (load 5.74 + tool 5.33 + export 2.75 + read) and 12.7 s for `passthrough` run 1 (export 5.75 + load 5.82); the second and third run took 6.5 and 3.9 s | same effect at twice the size, on the first big allocations of a cold VM; not memory pressure in the reclaim sense |

Evidence for the cause, from `benchmarks/shm_breakdown.py` (the worker's steps replayed one by one in a fresh process, 5 repeats, 512 MiB):

| step | as-is: wall median [min-max], system CPU | prewarmed: wall median [min-max] |
|---|---|---|
| copy block to a new array | 0.216 [0.181-2.917], sys 0.12 | 0.203 [0.185-0.228] |
| copy again into already touched memory | 0.068 | 0.067 |
| tool: one new array | 0.267 [0.174-2.709] | 0.149 [0.140-0.273] |
| `tifffile.imwrite` (disk) | 0.247 [0.150-3.186] | 0.140 [0.124-0.146] |
| `tifffile.imread` (page cache) | 2.266 [2.207-2.961], **sys 2.21** | 0.178 [0.153-0.192] |

The user CPU of every step is about 0.07 s (memory bandwidth); the rest is kernel time faulting in memory. A micro-benchmark (allocate and fill 512 MiB six times) gave 2.91, 0.12, 0.11, 0.10, 0.11, 1.10 s: bimodal, 0.1 s versus 1 to 3 s. Direct reclaim and memory pressure stall counters stayed at 0 in the 128 and 512 MiB runs (`k_pgscan_direct`, `k_allocstall_normal`, `k_psi_some_us`), so the slow steps are not reclaim. **Real memory pressure did appear at 1 GiB**: see 4.4.

Copy count, which is what transfers to real machines. Fresh 512 MiB buffers touched for one `invert` round trip:

| path | buffers | which |
|---|---|---|
| TIFF in, TIFF out (today) | 5 | page-cache pages (host write), worker array, tool output, page-cache pages (worker write), host array (the layer data) |
| block in, TIFF out | 5 | block pages replace the first buffer; nothing is saved |
| block in with a borrowed view (no worker copy), block out, host maps the block | 3 | block (host), tool output, result block; the host's layer is the mapping |

So shared memory by itself does not reduce copies; the borrowed read-only view in the worker (plan idea 2) and a result block the host maps without copying do. The prototype of the view (`view_max`) took 0.09 s at 512 MiB against 0.30 s for copy plus tool, and 545 MiB worker RSS against 1057 MiB (section 4.1 file `sandbox_prewarm_zero_copy.json`).

### 4.3 How a host should fill a block

`benchmarks/shm_fill.py`, 512 MiB, 4 repeats: filling through the mapping (what `multiprocessing.shared_memory` and a Java `MappedByteBuffer` do) 0.396 s; `write()` into the descriptor 0.184 s; `MAP_POPULATE` 0.404 s; plain anonymous memory 1.6 s median [0.15-2.85]. A Python host that wants the minimum should create the block and `os.write` into its descriptor, not fill the mapping page by page.

### 4.4 Memory

* Worker RSS at 512 MiB: 547 MiB (TIFF read), 1059 MiB (block mapped plus copy), 545 MiB (borrowed view). The block is shared memory, not evictable without swap.
* `shm_bench` at 1 GiB, `invert`, shared input: host array 1 + block 1 + worker copy 1 + tool output 1 + result 1 (tmpfs) is 5 GiB with about 6 GiB available: the worker was SIGKILLed by the OOM killer (`code -9`, "out of memory?" in the host message), and the run aborted. The disk path of the same task finished three times because its input was clean, evictable page cache. This was the only run in this work that hit real memory pressure. A block per image is a hard commitment of RAM (and on Windows of commit charge) for the whole run.

### 4.5 No-protocol alternative: the worker maps the TIFF

`benchmarks/tiff_memmap.py`, 512 MiB uncompressed TIFF, read-only memmap versus `imread`, then one full pass:

| cache | `imread` load + pass | `tifffile.memmap` load + pass |
|---|---|---|
| warm | 0.192 s | 0.037 s |
| cold | 0.576 s | 0.239 s |

No private copy and no extra resident memory (the pages are the page cache). Constraints: only uncompressed, contiguous TIFFs (what Napari, Fiji and tifffile write); the mapping must be copy-on-write (`mode="c"`) so a tool that modifies its input cannot change the host's file; on Windows an open mapping blocks deleting the file, so the worker must drop it before `COMPLETION` and the host's `rmtree` and `prune` must tolerate a late release. This is the plan's idea 3; it is independent of everything below.

### 4.6 What the Java hosts pay (Fiji's ImageJ 1.54p, JDK 21, same sandbox)

`benchmarks/java/FijiExportBench.java`, 512 MiB (16384 x 16384 `ShortProcessor`), 9 samples: `FileSaver.saveAsTiff` **0.83 s [0.39-2.75]**; `Opener.openImage` of the result **0.78 s [0.55-0.93]**; Appose `SharedMemory.create` plus `ShortBuffer.put(short[])` **0.32 s [0.30-0.42]**; block to a new `short[]` **0.38 s [0.16-0.43]**. At 128 MiB everything is 0.1 to 0.2 s. The shared path is steady where the TIFF path is erratic, and it is about 2 to 2.5 times faster at the median for the whole export plus import. That is 0.5 s on the way out and 0.4 s on the way back per 512 MiB image.

## 5. Feasibility per host

| Host | Block from the host's own data, directly | Copies before the block | Verdict |
|---|---|---|---|
| Napari | yes (`SharedMemory` plus `np.copyto`) | 1 (layer array to block); 0 extra for numpy, 1 extra for dask/zarr unless stored chunk by chunk | **no gain on input; maybe on results** |
| Fiji | **yes**, with the Appose `SharedMemory`/`NDArray` already shipped | 1 (`short[]` plane to block) | **yes, first host** |
| QuPath | **maybe**: JDK-only works on Linux only; Windows and macOS need JNA or FFM | 2 to 3 (tile cache, `BufferedImage`, conversion) | **no, not now** |

### 5.1 Napari (Python)

* **Direct from layer data.** `export_layer` already does `np.asarray(layer.data[0] if multiscale else layer.data)`; the block version is `np.copyto(np.ndarray(shape, dtype, buffer=block.buf), data)`: **one copy** for numpy data, correct for non-contiguous input (transpose, strided slice and Fortran order all land in a C-ordered block with identical pixels, `benchmarks/shm_lifetime.py` T5); a dask or zarr layer needs `dask.array.store` into the view to avoid a temporary. RGB layers (`picked`) copy one colour channel. The 4 GiB `MAX_EXPORT_BYTES` guard stays.
* **Measured gain.** Export of 512 MiB: tifffile write 0.14 s versus block fill 0.40 s (mapping) or 0.18 s (`write()`); worker load 0.18 s versus 0.25 s. Nothing to win.
* **Results.** The only real Napari gain is mapping a result block as the layer's data (no TIFF decode, no allocation, about 0.2 s and 512 MiB saved at 512 MiB). Hazard measured: on Python 3.11 `SharedMemory.close()` (and `SharedMemory.__del__`) with a live numpy view on `shm.buf` **raises nothing and the view then segfaults** (T4). A shared-memory layer must hold an `mmap` object (T4b: `mmap.close()` under a live array raises `BufferError`, and the array keeps the mapping alive), not a bare `SharedMemory`.
* **Lifetime and crash.** Host `SIGKILL` with its resource tracker alive: the tracker unlinks the block (T1). Host and tracker killed together (process group, a crashed IDE or terminal): **the block stays in `/dev/shm`** (T2), so a start-up sweep is needed. POSIX allows unlinking while mapped (T3), so a host that maps a result can unlink it at once.
* **Windows.** `multiprocessing.shared_memory` creates a **pagefile-backed named section** (`CreateFileMapping(INVALID_HANDLE_VALUE, ..., name)`): no file, freed when the last handle closes (a crashed host leaves nothing), but it counts against the commit limit and can be paged out; the worker must open the name while the host still holds its handle. Python does not add `Local\` and Appose adds it for Java: both name the session-local object. Unverified here.
* **macOS.** POSIX shm: no filesystem entry, so no sweep by listing; names are limited to 31 characters (Python's `psm_xxxxxxxx` and Appose's 14-character names fit); size is rounded to the page size (16 KiB on Apple silicon) and a block survives a crashed creator until reboot unless something unlinks it (Python's resource tracker does, T1 logic). Unverified here.

### 5.2 Fiji (Java 8 bytecode, Groovy script and jar)

* **Java version.** The jar targets Java 8 bytecode ("runs in every Fiji bundle, Java 8 to 21", `pom.xml`). The current "Fiji with Java" distribution used in the project's clean-sandbox test was Java 21.0.7 (`docs/CLEAN_TEST_REPORT_2026-10-06.md`); older bundles ship an 8. Whatever is chosen must run on 8.
* **Options checked, each with a result.**
  * **Appose `SharedMemory` / `NDArray` (JNA)**: `shm_open` + `ftruncate` + `mmap` on Linux, a bundled helper dylib on macOS (shm_open is variadic), `CreateFileMapping("Local\\" + name)` on Windows. It is the class the host already depends on (the Fiji host drives the worker with `org.apposed.appose.Service`; Appose 0.12.0 is what issue #66 cites). I compiled its 0.12.0 shm sources with `--release 8` against JNA 5.14 and ran a **real proof**: a Java process filled a `short[]` of random 16-bit values into an Appose block and the **real LabConstrictor worker** read it; the sum of all pixels, the first pixel, the shape and dtype matched exactly (`benchmarks/java_shm_proof.py --mode appose`: PASS, 32 MiB and 512 MiB). Byte order and unsigned values survive because the proof sets the buffer to native order explicitly (a plain big-endian `ByteBuffer` would not match numpy). Appose is only prior art for the user's parked decision, but the Fiji host already loads it, so this is no new dependency.
  * **`MappedByteBuffer` on a file in `/dev/shm` (JDK only, Java 8+)**: PASS (`--mode mmap`), 0.32 s for 512 MiB. Linux only. Is it "not on disk"? On Linux `/dev/shm` is tmpfs: RAM, yes. On macOS there is no tmpfs path; a RAM disk needs privileges. On Windows a mapped temp file is file-backed: the cache manager still writes the dirty pages to disk later, Defender may scan it, and Java cannot unmap a `MappedByteBuffer` deterministically on 8 to 21, so the file stays locked and cannot be deleted while the process lives. So **a mapped temp file is "not on disk" only on Linux.**
  * **Java 21 Foreign Function and Memory API**: PASS with `--enable-preview` (`--mode ffm`, `shm_open`/`mmap` straight from libc). It is a preview API in 21 (final in 22), needs a JVM flag Fiji's launcher does not set and does not exist on 8 to 20: **no**.
  * **JNI**: would need a compiled library per OS: no. **ImgLib2**: no shared-memory support of its own (it can wrap a `ByteBuffer`, which Appose provides). Appose-like approaches are covered above.
* **Copies.** `ImagePlus` holds one `short[]`/`byte[]`/`float[]`/`int[]` per plane: one copy per plane into `block.buf(from, to)`. A `ByteBuffer` is limited to 2 GiB, so a larger image is filled in per-plane windows of one block (the block itself can be larger; the descriptor is unchanged). Stack axis order (ImageJ is channel, then Z, then T interleaved) and RGB (`int[]` to uint8) need explicit mapping to the declared axes; calibration stays explicit parameters.
* **Lifetime.** Appose creates with unlink-on-close. The host closes it in the existing `finally` (`closeWorker` path), including cancel and kill. A crashed Fiji leaves a block on Linux and macOS (no tracker in the JVM), nothing on Windows.

### 5.3 QuPath (Groovy on QuPath's JVM)

* **How pixels leave QuPath.** `ImageWriterTools.writeImageRegion(server, RegionRequest, path)`: tiles come from the `ImageServer` (decoded, possibly cached), are assembled into a `BufferedImage` (packed `int` ARGB for RGB images, `DataBufferUShort`/`Float` bands for fluorescence), then encoded. Before any block exists there are already 2 copies (server read plus the assembled `BufferedImage`), plus a third to reorder bands or unpack ARGB into the bytes numpy expects. The block would replace only the final encode and the file, and it must run through `BufferedImage` raster access (`getDataElements` per band) because the layout is not the worker's.
* **Scale.** The host refuses anything above 100 megapixels per plane (`MAX_EXPORT_PIXELS`), 200 MB for one 16-bit channel; large slides are read in regions whose decode time (JPEG, JPEG 2000) is of the same order as the TIFF write. The saving is a fraction of a second per run.
* **Mechanism.** The host has its own `LcWorker` (no Appose), so the descriptor goes through `Gson` easily, but the memory side is open: QuPath runs a bundled JDK (21, I believe, not verifiable here); JDK-only `MappedByteBuffer` on `/dev/shm` works only on Linux; I could not establish whether QuPath's `lib/app` contains JNA (`build.sh` compiles against `$QUPATH/lib/app/*`; check that folder). FFM is preview in 21. **Verdict: no for now**; revisit only if QuPath is changed to read regions into a worker-native layout and measured to matter.

## 6. Protocol implications

Everything is additive within protocol 1; nothing below changes the TIFF path.

1. **Descriptor** (input, already accepted): `{"appose_type": "ndarray", "shm": {"name": "<block name>"}, "shape": [Y, X] or [Z, Y, X] ..., "dtype": "uint16"}`. Required additions to the worker, before any host sends one in anger:
   * **`order`**: Appose's Java `NDArray.Shape` has an `Order` (C or F) and an ImgLib2-style host naturally has x fastest with shape `[x, y]`. The worker ignores `order`, so such a descriptor would be read **transposed with no error**: wrong science. Rule: a descriptor with `order` other than `C` is `unreadable_image`, or honoured with `np.ndarray(..., order="F")`; hosts must send C-order shapes (`[Y, X]`) anyway. Add a test with a non-square image.
   * The shape must be consistent with the declared `axes` (issue #56) and the block size is checked before mapping; refuse more than a configured maximum.
2. **Feature flag**: `shm_input_v1` in `features.py` and in the PROTOCOL.md feature table: "the worker validates shared-memory image descriptors (order, size, dtype) and never unlinks a host block". A host sends a descriptor only when the schema's `features` list contains it (compat rules 2 and 3 already handle a missing list: refuse or file path). A schema without it means "send a TIFF". Never ask an unknown worker and fall back after partial work.
3. **Results (not recommended yet)**: a reserved input `_transport: {"image_out": "shm"}` (an old worker ignores it by `reserved_inputs_v1` and answers with a `path`, so the host falls back by looking at the answer) and a result `{type, name, axes, shm: {name}, shape, dtype}` with feature `shm_output_v1`. Ownership: the worker creates and detaches without a tracker (as `convert._attach_shared_memory` does for reading), the host maps, **unlinks at once**, and owns the mapping. Costs that are not technical: the results folder then holds no image file, so "keep my results", run records and `prune` expectations change; a durable copy has to be an explicit `FileOut`, as the issue already says.
4. **Run records and commands** must show the original source (file path or layer name), never the block name (`runs.record`, `command.py`, the "Copy as command" snippets): a block name is meaningless after the run.

## 7. Cleanup, retention, crashes, Windows locking

* **Blocks are not result folders.** They are never under `results/` or `runs/`, carry no `.lc-owner.json` or `.lc-done.json` and are never touched by `prune` (which only deletes marker-owned finished folders). The retention contract is unaffected for inputs. For shared results see 6.3.
* **Naming and ownership.** Name `lc_<hostpid>_<random>` (Linux `/dev/shm/lc_...`; at most 31 characters including the slash for macOS). The host writes the name into `<LC_HOME>/state/shm-<pid>.json` before creating it and deletes the file after unlinking.
* **Crash leftovers.** Host killed alone: Python's tracker removes the block (T1); the JVM has no tracker. Host and tracker both killed, or a JVM killed: Linux leaves `/dev/shm/lc_*` (T2); macOS leaves a kernel object until reboot or unlink; Windows leaves nothing. Remedy: at host start, read `state/shm-*.json` of dead pids and unlink those names (macOS) and glob `/dev/shm/lc_*` with a dead pid (Linux). This sweep is separate from `prune` and must never touch `results/` or `runs/`.
* **Worker side.** The worker never unlinks a host block (documented and tested). If the worker is killed mid-copy the host still owns the block and unlinks it in its `finally`. On Windows the worker closing its handle early is harmless.
* **Windows file locking.** The TIFF path already has the problem that a host `rmtree` of the job folder can fail while Defender or a viewer holds the file; blocks have no file. A memory-mapped TIFF in the worker (4.5) reintroduces it unless released before `COMPLETION`. Java file mappings (`MappedByteBuffer`) cannot be released deterministically on Java 8 to 21: do not use them on Windows.

## 8. Recommended design (Fiji first)

1. **Tools** (prerequisite, about 3 days): validate `order` and size in `_ndarray_from_shared_memory`; add `shm_input_v1` and its PROTOCOL.md row; a small `labconstrictor_tools.shm` helper (name scheme, create with `write()` fill, mmap-owning array, sweep); tests on Linux, macOS and Windows runners (attach, stale name, wrong order, wrong size, non-square image, worker killed); keep the copy in the worker (the borrowed view is a separate item with its own opt-in marker).
2. **Fiji** (about 4 to 5 days plus 2 to 3 days of Windows and macOS testing): in `exportOpenImage`, when the schema lists `shm_input_v1`, the image is at least 256 MiB (a setting, default off at first) and the tool input is an open image: create an Appose `NDArray`, fill per plane, send the descriptor, close in `finally`; any exception before the send falls back to the TIFF path; axis and RGB mapping with round-trip tests against the TIFF path (identical arrays for uint8, uint16, float32, RGB, stacks, a non-square image). Files chosen by the user are never copied into a block (the file path is already optimal).
3. **Measure on real Windows and macOS machines**, with Defender on, a spinning or network temp folder and a 1 to 2 GiB image, before any default change. Decision rule: default-on only if the median gain is at least 1 s at 512 MiB and the peak memory does not exceed the TIFF path by more than one image.
4. **Later, only if justified**: the worker's borrowed read-only view; results as blocks for Napari and Fiji as display-only previews.

Total effort for steps 1 and 2: about 2 weeks including review and the three-OS run. Napari and QuPath: not scheduled.

## 9. Risks

* Memory: an extra, unevictable image per run (section 4.4); mitigate with the threshold, a free-memory check (refuse and use the TIFF path when available memory is below 3 times the image) and releasing the host-side copy early.
* Silent wrong pixels: axis order, `order`, byte order, signedness, ImageJ's channel-first stack order, 2 GiB `ByteBuffer` windows. Mitigation: the `order` check, the round-trip tests above, the TIFF path kept as the reference.
* Leaks after crashes (section 7) and Windows commit charge.
* Platform divergence: Linux proven here, Windows and macOS only read; a macOS helper dylib inside Appose; JNA availability in Fiji and QuPath bundles.
* Product semantics of shared results (6.3).
* The measured gain is small on a warm cache; a user with a fast SSD and an image under 256 MiB gets nothing.

## 10. What I could not verify

* Windows and macOS behaviour of every item (named sections, commit charge, shm name limits, helper dylib, Defender). Section 5 and 7 statements for those OSes are from documentation and source reading.
* Real Fiji, QuPath and Napari runs (GUI, ImageJ stack layouts, `BufferedImage` conversion cost, display time of large results). The Fiji numbers are ImageJ 1.54p library calls in a headless JVM.
* Which Java versions current Fiji bundles ship beyond the 21.0.7 recorded in the clean-test report, and whether JNA and Appose 0.12.0 are in a given Fiji bundle (the host script imports Appose, so it must be; not checked in a Fiji install).
* QuPath's bundled JDK and whether its `lib/app` contains JNA.
* Slow disks, network folders, antivirus: the sandbox disk reads at 1.5 GB/s warm or cold, which a user's will not.
* The 1 GiB shared round trip never completed (OOM), so there is no 1 GiB number for it; a bigger machine is needed.
* Maven Central returned HTTP 429, so Appose was compiled from its 0.12.0 sources (fetched from GitHub raw, `--release 8`) with JNA 5.14.0 from Maven Central, not taken from the released jar.
* Statistical weight: 3 runs per cell (the user's request), 9 for the Java numbers; spreads are shown because they are large and the sandbox is shared.

## 11. Reproduce

```
python -m pip install numpy tifffile pandas
python benchmarks/shm_bench.py --sizes 128 512 1024 --repeats 3 --cli --json out.json   # default mode
python benchmarks/shm_bench.py --sizes 128 512 --repeats 3 --prewarm 2 --json out2.json  # prewarmed
python benchmarks/shm_bench.py --sizes 512 --tools image_max --cold --prewarm 2          # drops the page cache (root)
python benchmarks/shm_bench.py --sizes 1024 --tools passthrough --no-readback --out-scratch /dev/shm/x   # memory-careful 1 GiB
python benchmarks/shm_breakdown.py --mb 512 --repeats 5 [--prewarm]
python benchmarks/shm_fill.py --mb 512
python benchmarks/tiff_memmap.py --mb 512 [--cold]
python benchmarks/shm_lifetime.py                    # Linux: crash, unlink and view hazards
python benchmarks/shm_table.py benchmarks/results/*.json
# Java (JDK 21; Appose 0.12.0 jar or its sources, JNA 5.14 and jna-platform on the class path; ij-1.54p for FijiExportBench):
javac --release 8 -cp appose.jar:jna.jar -d out benchmarks/java/ShmProof.java benchmarks/java/FijiExportBench.java
javac --release 21 --enable-preview -d out benchmarks/java/ShmProofFfm.java
python benchmarks/java_shm_proof.py --mode appose|mmap|ffm --classpath out:appose.jar:jna.jar:jna-platform.jar
java -cp out:ij.jar:appose.jar:jna.jar:jna-platform.jar FijiExportBench 16384 3 /tmp
```

The harness aborts and removes its scratch folders when `MemAvailable` falls below 700 MiB (`--guard-mib`), because the machine it was written on is shared.
