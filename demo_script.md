# Demo script — 4 minutes

Judges are standing at the desk, watching your screen. You drive.

The problem statement below is lifted from the project README and
`gapcheck/README.md`. Say it in your own rhythm, but do not invent new
claims at the desk — everything here is something the code actually does.

---

## Before they arrive

Four terminals already running, arranged so all four are visible at once:

```
+---------------------+---------------------+
|  T1  SuperLink      |  T2  manufacturer_a |
+---------------------+---------------------+
|  T3  manufacturer_b |  T4  manufacturer_c |
+---------------------+---------------------+
```

A fifth window on top, half-screen, is your **driver terminal (T5)** — the
only one you type in. Browser open with three tabs, in this order:

1. `out/dashboard.html`
2. `https://github.com/npztech/federated-gapcheck`
3. Flower Hub — `@npztech/gapcheck`

Start on T5 with the screen cleared. Do a throwaway `flwr run` five minutes
before they arrive so the app environment is warm — otherwise the first run
of the day spends a minute installing dependencies while they watch.

---

## 0:00–0:40 — The problem

*Nothing on screen yet but the four terminals. Let them see there are four.*

> A UK Responsible Person is legally accountable for the technical files of
> manufacturers it has never audited, usually overseas. Those files are
> commercially sensitive, and often incomplete.
>
> Today the UKRP has two options. Ask for the entire technical file — which
> manufacturers resist, and which hands the UKRP a custody problem it does
> not want. Or take their word for it.
>
> Neither is good enough. And notice that what the UKRP actually needs is
> much smaller than the file: *which of the twelve required documents
> exist, and are they usable?*

*Gesture at the four terminals.*

> One coordinator. Three manufacturers — Ningbo, Shenzhen, Guangzhou. Each
> of those three is a separate process holding a folder that the other two,
> and the coordinator, cannot read.

---

## 0:40–1:30 — Run it

*Type in T5. Say this while it runs.*

```bash
flwr run gapcheck demo --stream
```

> The coordinator is sending one thing outward: the checklist. Twelve
> requirements under the UK Medical Devices Regulations 2002. It is generic
> — the same twelve for every manufacturer, no client data in it.
>
> Each node is now reading its own technical file, on its own machine, and
> deciding for itself what to say back.

*Point at T2, T3, T4 as their log lines move.*

Output lands:

```
manufacturer_a   present 12  incomplete  0  missing  0   readiness 100%
manufacturer_b   present  7  incomplete  1  missing  4   readiness  62%
manufacturer_c   present  2  incomplete  5  missing  5   readiness  38%

documents inspected  : 26
documents transferred: 0
```

---

## PAUSE 1 — the last two lines

*Stop talking. Put the cursor on those two lines. Three full seconds of
silence. Let them read it themselves before you say anything.*

> Twenty-six documents were read. Zero were sent.
>
> That second number is not a counter that happens to be zero today. There
> is no code path in the node agent that puts document content into the
> reply. It returns a requirement id, a status, and a sentence. If someone
> added a path that returned content, that field would have to change — and
> that is written down in the module, as an instruction to whoever edits it
> next.

---

## 1:30–2:30 — The dashboard

*Switch to browser tab 1, `out/dashboard.html`.*

> Same data, rendered. Green is present, amber is present-but-not-usable,
> red is missing. Manufacturer A is ready. C is not.

*Hover the **manufacturer_c** row, column **R10**.*

---

## PAUSE 2 — the R10 tooltip

*Let the tooltip sit there. Read it out loud, slowly.*

> **Document present but cites EU MDR rather than UK MDR 2002; marked as
> draft or unfinished.**

*Beat.*

> That is the finding a UKRP actually needs. Their declaration of conformity
> exists — so a checklist that only asked "do you have one?" would have said
> yes. But it cites the wrong regulation. It is an EU document in a GB
> submission, and it would have failed.
>
> And look at what the coordinator was told, and what it was not. It knows
> requirement ten is not usable, and why. It does not have the document. It
> does not have an excerpt. It does not even have the filename.

---

## 2:30–3:15 — Who is on the other end

*Switch to T2 (manufacturer_a's terminal). Point at its startup line.*

> Each node was started by its own operator, with its own folder path.

---

## PAUSE 3 — the roster

*Turn away from the screen. Say this to the judges, not the laptop.*

> The coordinator does not hold a list of clients. It asks whoever is
> connected. The nodes report their own identity — that name in the results
> came from the node, not from a roster on the coordinator's side.

*Beat.*

> Which is what you want. Onboarding a manufacturer is that manufacturer
> starting a process and pointing it at their own folder. Nobody sends
> anybody a technical file. And the coordinator cannot enumerate clients it
> was never told about.

---

## 3:15–3:50 — It is real and it is public

*Browser tab 2 — GitHub.*

> Open source, Apache 2.0.

*Scroll to show `gapcheck/` and `run_local_demo.md`.*

> The whole thing reproduces from that document — four terminals, three
> nodes, and the commands are the ones we actually ran.

*Browser tab 3 — Flower Hub.*

> And published to Flower Hub as `@npztech/gapcheck`, so it installs the
> way any Flower app does.

---

## 3:50–4:00 — Close

*Stop clicking. Face them.*

> Two things to be straight about. Every document you just saw is
> synthetic — nothing in this repository is a real client file. And the
> privacy property is disclosure minimised by design, not proof: the node
> chooses what to disclose, and it is self-reporting. A manufacturer
> running a modified agent could lie. That limit is documented in the
> README alongside the others — keyword matching rather than comprehension,
> and applicability that the agent flags rather than guesses.

*Stop. Do not fill the silence.*

---

# Fallback — 30 seconds

## A node misbehaves, or a run returns `NO RESULT`

Seen once today: a SuperNode's task token fails to authenticate and the run
times out with no findings. Recovery is reliable.

**Ctrl+C the three SuperNode terminals. Restart all three. Run again.**

Say, while typing, without apology:

> One of the nodes dropped its session — restarting it. This is three
> independent machines in the story, so any one of them can go away.

That is a true statement about the architecture, and it costs you 30
seconds. The commands are the three `flower-supernode` lines in
`run_local_demo.md`.

## Everything is broken

Do not debug in front of judges. Switch to the local runner:

```bash
cd agent
python coordinator.py
```

Then open `out/dashboard.html`. Say:

> Same logic, local runner — the federation ran all morning.

Then carry on with the dashboard from **1:30**. The findings, the R10
tooltip, and both pauses that depend on them are identical, because it is
the same checklist and the same matching code. You lose the four-terminal
picture and nothing else.

## If a judge asks why it fell over

> Windows, conference wifi, and a laptop that rebooted an hour ago. The
> federated path ran clean six times this morning, and the committed
> `out/findings.json` is from one of those runs.

---

# Cue card

| Time | Screen | Do |
|---|---|---|
| 0:00 | four terminals | the problem, gesture at the three nodes |
| 0:40 | T5 | `flwr run gapcheck demo --stream` |
| 1:20 | T5 output | **PAUSE 1** — 3s silence on `transferred: 0` |
| 1:30 | dashboard.html | green / amber / red |
| 1:50 | hover c × R10 | **PAUSE 2** — read the EU MDR finding aloud |
| 2:30 | T2 | **PAUSE 3** — no roster, nodes self-report |
| 3:15 | GitHub → Hub | Apache 2.0, reproducible, published |
| 3:50 | face them | synthetic · minimised by design · self-reporting limit |

**Three-minute cut:** drop 3:15–3:50. Mention GitHub and Hub in one
sentence over the dashboard instead of switching tabs. Keep all three
pauses — they are the demo.
