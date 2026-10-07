# Spec (proposal): run an app on a server, drive it from Fiji, Napari or QuPath on a laptop

Status: **proposal for review, nothing is implemented.** Today remote execution is not supported (see OPERATIONS.md).

## 1. The three situations

| # | Situation | Works today? |
|---|---|---|
| A | Everything on the server, used through remote desktop, VNC or X forwarding; or a headless Jupyter server with the notebook | Yes, nothing to add |
| B | **Host on a laptop, worker on a server** (one GPU machine for many laptops) | No: this spec |
| C | Shared server with many users and a job queue (SLURM and similar) | No: out of scope here, see section 9 |

## 2. Goals and non-goals
Goals
1. A person picks a *remote* app in the normal host list and uses it like a local one: same form, progress, cancel, results.
2. No new open port and no new account system: the transport is the user's own SSH login.
3. Nothing changes for local apps; tools do not know whether they run locally or remotely.
4. A dropped connection never leaves an orphan process or a half-written result.

Non-goals: running tools without a login, a web service, a job scheduler, sharing one worker between users, streaming very large images faster than the network allows.

## 3. Design in one picture

```
laptop                                         server
host (Napari/Fiji/QuPath)                      sshd
  registry entry kind=ssh  --- ssh ---------->  python -m labconstrictor_tools serve --module M --exit-on-eof
  JSON lines on stdin/stdout  <-------------->  (the unchanged worker protocol)
  inputs  --- sftp upload  ------------------->  <remote_job_dir>/in/...
  results <-- sftp download --------------------  <remote_job_dir>/out/...
```
The worker protocol is already JSON lines over stdin and stdout, so it passes through an SSH session unchanged. The only new things are how a worker is started and how files travel.

## 4. Registry entry for a remote app (`<registry>/<name>.json`)
Existing fields stay. New fields, all optional (absent = local):

| Field | Meaning |
|---|---|
| `transport` | `"local"` (default) or `"ssh"` |
| `ssh.host`, `ssh.user`, `ssh.port` | where to connect (also resolved through the user's `~/.ssh/config`, so a Host alias is enough) |
| `ssh.identity` | optional key file; otherwise the agent or `~/.ssh/config` |
| `ssh.remote_python` | the app's interpreter on the server (the `python` field then means the remote path) |
| `ssh.remote_home` | the server's `LC_HOME` for job folders (default `~/.labconstrictor`) |
| `ssh.env` | extra environment on the server, for example `CUDA_VISIBLE_DEVICES=1` to choose a GPU |

Registration: `labconstrictor-tools register-remote --name X --host gpu1 --python /opt/app/bin/python --module X_lc_tools` connects once, reads the schema from the server (`labconstrictor-tools describe --module ...`) and stores it locally next to the entry. `labconstrictor-tools refresh X` re-reads it after the app is updated on the server. Hosts still read the schema from the local file, so listing and form building need no connection.

## 5. Connection
- The host runs the system `ssh` program (no SSH library to ship or secure), batch mode, so it never blocks on a password prompt: key or agent authentication is required. A clear message tells the person how to set it up when it fails.
- Host key checking stays on (`StrictHostKeyChecking=yes`); the first connection is made by `register-remote` where the person confirms the fingerprint once.
- `ControlMaster auto` and `ControlPersist` reuse one connection for the worker and the file transfers, so a run does not pay a login each time.
- A keep-alive (`ServerAliveInterval`) detects a dead link in under a minute.

## 6. Files
A tool receives paths. Remotely, the host must make the inputs exist on the server and bring the results back:
1. The host writes the inputs exactly as today (temporary TIFF and CSV in a local job folder).
2. It uploads them to `<remote_home>/jobs/<job id>/in/` (SFTP over the same connection; large files are compressed only when the link is slow, never lossy), and rewrites the input paths in the request to the remote paths.
3. The worker runs with `_job_dir` = `<remote_home>/jobs/<job id>/out/`.
4. On COMPLETION the host downloads every path named in the results to the local job folder and rewrites the result paths. Hosts then show them exactly as today.
5. The remote job folder is deleted after a successful download, or after 24 hours by a sweep when the worker starts.

Rules: results are downloaded only if they are inside the job folder (a tool cannot make the host fetch `/etc/passwd`); a size limit with a clear message; a progress line "uploading 340 MB / downloading 12 MB" appears before and after the tool's own progress.
Existing local-path inputs given as files ("or file", Folder inputs): a path that exists on the laptop is uploaded; a `server:` prefix means "already on the server" (a shared data folder), which avoids uploading terabytes. The form shows which one it is.

## 7. Progress, cancel, failure
- UPDATE, COMPLETION, FAILURE, CANCELATION pass through unchanged.
- Cancel sends the usual CANCEL line; if the tool ignores it, the host closes the SSH session and the server worker (started with `--exit-on-eof`, new) ends when its stdin closes, killing its process group. No orphan.
- A dropped link: the host reports "connection lost", the server worker exits on end of input, the host offers "Run again". Resuming a running job after a drop is a later extension (the worker would keep the job and the host would reattach by job id).
- Remote crash output (`stderr`) is shown in Details like a local one.

## 8. Security
- Same model as today: only tools declared by the app's own module can run; the host sends `lc:<tool>` and inputs, never code.
- The server's own account controls what the tool can read and write; the SSH login is the only door. No port is opened and no credential is stored by LabConstrictor (keys stay with the user's SSH setup).
- A remote entry is a registry entry like any other: the existing ownership and permission checks apply to the local file; `ssh.host` is shown in the host list so a remote app is never mistaken for a local one.
- The host never writes outside its job folders; downloads are confined as in section 6.

## 9. Not in this proposal (and why)
- **Job queues (SLURM, etc.):** a different model (submit, wait, fetch). It would be a second transport (`transport: "slurm"`) that wraps the same worker in a batch job; worth doing only if a lab asks.
- **A web service or Jupyter kernel gateway:** adds a server to secure and operate; SSH is already there on every GPU machine.
- **Shared memory over the network:** impossible; the files-based design is why this works.

## 10. Work breakdown
1. Tools: `transport: ssh` in registry and `client.WorkerProcess` (start command, `--exit-on-eof`, remote schema fetch, `register-remote`, `refresh`, `doctor` checks).
2. Tools: file transfer (upload inputs, path rewriting, confined download, cleanup sweep) with unit tests against a local `sshd`.
3. Hosts: show "remote" in the app list and the transfer progress line; nothing else changes (Napari first, then Fiji, then QuPath).
4. Tests: a CI job with an `sshd` container (localhost) running the example app and the stress tools: cancel, kill the link, big files, wrong key, host key change; plus a real run on a GPU machine.
5. Docs: `OPERATIONS.md` section for administrators (install the app on the server, create the users' keys, `register-remote`).

## 11. Questions for the lab
1. Which of A, B, C is the real need? (This spec covers B.)
2. Do users have key-based SSH to the server today?
3. Is the data usually on the laptop (upload) or already on the server (shared folder)? That decides how much effort goes into the transfer.
4. Is one GPU shared by several users at once (then a queue matters)?
