# Running the federated gap check locally

Three manufacturers, three SuperNodes, one coordinator, on one laptop.
Every command below was executed on this machine on 26 Aug 2026 — this is
a transcript, not a guess.

You need four terminals: one SuperLink, three SuperNodes. The `flwr run`
command can go in any of them once the others are up.

---

## 0. One-time setup

`flwr` is installed as a uv tool, so `flwr`, `flower-superlink` and
`flower-supernode` are already on PATH. Check:

```bash
flwr --version
```

**Set the console encoding first, in every terminal.** Flower prints emoji;
the Windows default code page (cp1252) cannot encode them and the command
dies with `UnicodeEncodeError`.

```bash
export PYTHONIOENCODING=utf-8
```

PowerShell instead:

```bash
$env:PYTHONIOENCODING = "utf-8"
```

Then tell the CLI where the SuperLink is. Create `%USERPROFILE%\.flwr\config.toml`:

```toml
[superlink]
default = "demo"

[superlink.demo]
address = "127.0.0.1:9093"
insecure = true
```

---

## 1. Terminal 1 — SuperLink

```bash
flower-superlink --insecure --isolation subprocess
```

Wait for these three lines:

```
Flower Deployment Runtime: Starting Control API on 0.0.0.0:9093
Flower Deployment Runtime: Starting Fleet API (gRPC-rere) on 0.0.0.0:9092
Uvicorn running on http://127.0.0.1:8000
```

- `9093` Control API — where `flwr run` submits.
- `9092` Fleet API — where SuperNodes connect.
- `8000` Runtime API — where the ServerApp process talks back.

`--isolation subprocess` is the default; it means the SuperLink spawns
`flwr-serverapp` itself. Stated explicitly here so the command is portable.

State is in memory. Kill the SuperLink and every run is forgotten. Add
`--database state.db` if you want it to survive a restart.

---

## 2. Terminals 2, 3, 4 — the three SuperNodes

**Each SuperNode needs its own `--port`.** They all default to `9094` for
their Runtime HTTP API, so without this the second and third fail to bind.

Terminal 2 — Ningbo:

```bash
flower-supernode --superlink 127.0.0.1:9092 --insecure --port 9094 --node-config 'data-dir="C:/Users/ceprz/Documents/hackathon/nodes/manufacturer_a" node-name="manufacturer_a" display-name="Ningbo - infusion sets"'
```

Terminal 3 — Shenzhen:

```bash
flower-supernode --superlink 127.0.0.1:9092 --insecure --port 9095 --node-config 'data-dir="C:/Users/ceprz/Documents/hackathon/nodes/manufacturer_b" node-name="manufacturer_b" display-name="Shenzhen - clinical thermometers"'
```

Terminal 4 — Guangzhou:

```bash
flower-supernode --superlink 127.0.0.1:9092 --insecure --port 9096 --node-config 'data-dir="C:/Users/ceprz/Documents/hackathon/nodes/manufacturer_c" node-name="manufacturer_c" display-name="Guangzhou - orthopaedic supports"'
```

### About the quoting

`--node-config` takes one argument: space-separated `key=value` pairs whose
values are **TOML literals**. So the strings need quotes of their own,
surviving inside the shell's quotes.

**The bash form above does not work in PowerShell.** PowerShell strips the
inner double quotes when handing the argument to a native executable, so
the SuperNode receives `data-dir=C:/path/a` — an unquoted value that is not
valid TOML — and fails to parse it. Measured on 26 Aug:

```
bash        ->  argv[2] = data-dir="C:/x/a" node-name="manufacturer_a"   OK
PowerShell  ->  argv[2] = data-dir=C:/x/a node-name=manufacturer_a       BROKEN
```

In PowerShell, swap the quoting round: **double quotes outside, TOML
literal (single) quotes inside.**

```powershell
flower-supernode --superlink 127.0.0.1:9092 --insecure --port 9094 --node-config "data-dir='C:/Users/ceprz/Documents/hackathon/nodes/manufacturer_a' node-name='manufacturer_a' display-name='Ningbo - infusion sets'"
```

TOML treats `'...'` as a literal string, so this parses to exactly the same
config dict as the bash form. Verified through PowerShell's argument
passing and then through Flower's own `parse_config_args`.

Two forms that look like fixes and are not:

- **`--%`**, the stop-parsing token, switches to cmd.exe-style parsing,
  which does not understand single quotes. Given the bash line it yields
  `'data-dir=C:/x/a` and `node-name=manufacturer_a'` as two separate
  arguments. Do not use it here.
- **Doubling the inner double quotes** inside an outer double-quoted string
  gets stripped exactly like the single-quoted form.

Backslash-escaping the inner quotes does work in PowerShell, but it breaks
in bash — the wrong thing to write down for a command meant to be portable.

Use **forward slashes** in the path. A backslash is an escape character in
a TOML string and `"C:\Users\..."` will fail to parse.

Paths must be **absolute**. The SuperNode does not resolve them relative to
your repository.

Each node should print, within a second or two:

```
Uvicorn running on http://127.0.0.1:9094
SuperNode ID: 11951452491630369628
```

That ID is assigned by the SuperLink. Seeing it means the node is
registered and polling for work.

---

## 3. Start a run

```bash
flwr run gapcheck demo --stream
```

The first `gapcheck` is the app directory; `demo` is the SuperLink connection
name from `config.toml`. `--stream` follows the ServerApp's logs.

The first run installs the app's dependencies into an isolated environment
and takes about a minute. Later runs are a few seconds.

Expected output:

```
Distributing GB-CLASS-IIa-v1 to 3 node(s)...
Federated gap check complete.

  manufacturer_a   present 12  incomplete  0  missing  0   readiness 100%
  manufacturer_b   present  7  incomplete  1  missing  4   readiness 62%
  manufacturer_c   present  2  incomplete  5  missing  5   readiness 38%

  documents inspected  : 26
  documents transferred: 0

Written to C:\Users\ceprz\Documents\hackathon\out\findings.json
```

That last pair of numbers is the demo. 26 documents were read; 0 were sent.

### Overriding config

```bash
flwr run gapcheck demo -c 'output-dir="D:/elsewhere"' --stream
```

`output-dir` must be absolute — the ServerApp runs from the FAB install
directory under `~/.flwr/apps/`, not from this repository. Set it to `""`
to skip writing the file.

Other knobs: `checklist-version`, `round-timeout` (seconds the coordinator
waits for all nodes).

---

## 4. Read the results

```bash
flwr log <run-id> demo --show
```

`--show` prints once and exits; `--stream` follows. Also:

```bash
flwr list demo
```

The findings themselves are in `out/findings.json`, one object per node,
same shape as the pre-federation `agent/coordinator.py` produced.

---

## Troubleshooting

**`UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f517'`**
You skipped `PYTHONIOENCODING=utf-8`. Set it and re-run.

**`No SuperNodes are connected to this SuperLink`**
The ServerApp raised this deliberately rather than printing an empty table.
Check each SuperNode terminal for a `SuperNode ID:` line. A node that
prints a bind error instead is fighting another node for port 9094 — give
it its own `--port`.

**`data-dir is not a directory`**
Backslashes in the TOML string, or a relative path. Use absolute paths with
forward slashes.

**A node reports 12 gaps when its folder is full**
`data-dir` points somewhere real but wrong. The ClientApp only reads `*.md`
directly inside that folder — it does not recurse.

**`Runtime task-token authentication failed` (401) on a SuperNode, and the
run times out with `NO RESULT`**
Seen once, on 26 Aug, on nodes that had already served one run. It did not
reproduce across three subsequent runs, including a run after changing the
app code without restarting the nodes — so the trigger is not understood.
The recovery is reliable: stop all three SuperNodes, start them again, run
again. If it happens during the demo, that is the move. Budget 30 seconds.

**`flwr run --stream` does not return after printing results**
The run has finished — the log stream just stays open. Ctrl-C is safe;
`out/findings.json` is already written. Use `--show` on `flwr log` if you
want a command that exits cleanly.

**Changing the app code**
No node restart needed. `flwr run` rebuilds the FAB, the SuperLink
redistributes it, and the SuperNodes pick up the new version. Verified.

---

## Shutting down

Ctrl-C each terminal. Nothing persists: the SuperLink's state is in memory,
and the SuperNodes hold no findings after they reply.

The installed app copies under `~/.flwr/apps/` and the runtime environments
under `~/.flwr/runtime-envs/` do accumulate. They are safe to delete.
