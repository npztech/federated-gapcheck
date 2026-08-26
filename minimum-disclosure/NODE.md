# Keep your technical file on your own machine

The other setup (`TEAMMATES.md`) uploads your technical file to SuperGrid to be
read there. This one does not. Your file stays on your disk, a Flower SuperNode
on **your** machine reads it, and only claims cross the network.

At the end of a run the coordinator prints `documents transmitted: 0`, and that
is literally true.

---

## 1. Get the code

```bash
git clone -b minimum-disclosure git@github.com:npztech/federated-gapcheck.git
cd federated-gapcheck/minimum-disclosure/local-node
uv sync
```

Already cloned? Just pull:

```bash
git pull
cd minimum-disclosure/local-node && uv sync
```

## 2. Put your technical file somewhere private

```bash
mkdir -p ~/manufacturer-files
cp ../fixtures/mfr_northwind.json ~/manufacturer-files/technical_file.json
```

That folder is yours. Nothing in the coordinator's app can change the path —
it is set by you, on the command line, in the next step.

## 3. Make a node key and register the node

```bash
ssh-keygen -t ed25519 -f ~/.flwr/node_key -N ""
uv run flwr supernode register ~/.flwr/node_key.pub supergrid
```

It prints a **SuperNode ID**. Send that number to Alp — he attaches it to the
shared federation:

```bash
# Alp runs this
uv run flwr federation add-supernode <node-id> @alpozaydin/conformity supergrid
```

## 4. Start your SuperNode and leave it running

```bash
uv run flower-supernode \
  --superlink supergrid.flower.ai:9092 \
  --auth-supernode-private-key ~/.flwr/node_key \
  --auth-supernode-public-key ~/.flwr/node_key.pub \
  --host 127.0.0.1 --port 9094 \
  --node-config 'data-dir="'$HOME'/manufacturer-files"'
```

Leave this terminal open. It polls for work. You do nothing else — the
regulator dispatches, your node answers, and you can watch it in this window.

---

## Try it entirely on your own machine first

If you want to see it work before wiring up to SuperGrid, run all three parts
locally. Three terminals.

**Terminal 1 — a SuperLink**

```bash
uv run flower-superlink --insecure
```

**Terminal 2 — your SuperNode**

```bash
uv run flower-supernode --insecure \
  --superlink 127.0.0.1:9092 \
  --host 127.0.0.1 --port 9094 \
  --node-config 'data-dir="'$HOME'/manufacturer-files"'
```

**Terminal 3 — the regulator**

Add this to `~/.flwr/config.toml` once:

```toml
[superlink.localdev]
address = "127.0.0.1:9093"
insecure = true
```

Then:

```bash
cd federated-gapcheck/minimum-disclosure/local-node
uv run flwr run . localdev --stream --run-config 'rulebook="uk"'
```

Expected:

```
Dispatching 4 clauses of UK to 1 manufacturer node(s)...

  Northwind Acoustics Ltd
    UK-EMC-1   PASS   measured=None   TR-4471 §3.1
    UK-RED-1   PASS   measured=None   TR-4472 §2.4
    UK-SAFE-1  PASS   measured=None   SAF-1180
    UK-MARK-1  PASS   measured=None   DOC-NW500-UK
    ledger: 2.0 bits

  documents transmitted: 0
```

Swap `rulebook="us"` to see the same device assessed against FCC rules.

---

## What actually left your machine

Four claims. Each one is a clause id, a verdict, the report reference it rests
on, and a note. `measured=None` because a threshold clause asks which side of a
limit you are on — that is one bit, and the measured value is more than the
regulation requires.

Your bill of materials, your suppliers, your costs, your schematics: read on
your machine, and discarded when the function returned.

## Notes

| | |
|---|---|
| `--clientappio-api-address` | removed in flwr 1.35 — use `--host` and `--port` |
| no `data-dir` | the node refuses the work rather than reporting an empty folder as failures |
| this path is deterministic | a ClientApp cannot call the model API, so clause matching here is mechanical. The language reasoning lives in the agent apps. The part that touches your secrets has no model in it. |
