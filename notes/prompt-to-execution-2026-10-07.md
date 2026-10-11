# Prompt to storm execution, 7 Oct 2026

> **Experimental. We are just trying this.**
>
> A number here is a log reading, not a claim. This is a pre-storm on the desk. It is not the 9 or 13 Oct storm, and it does not fill a public result section.

Read [DISCLAIMER.md](../DISCLAIMER.md).

The first score below is the reading at 2026-10-07T18:35:32Z. The run was stopped at 2026-10-07T18:38:49Z. The close is at the bottom.

## How long

The desk started on the prompt at **2026-10-07T17:36:23.992Z**.

The first submit second that stayed up was **2026-10-07T17:48:18.564Z**.

**11 minutes 55 seconds** (714.6 seconds).

A shell-tied launch submitted at **2026-10-07T17:45:23.386Z**, 8 minutes 59 seconds after the prompt. Those processes died when the shell closed. That launch is not this score.

The 12 minutes were the plan read, the three-machine recheck, the clock, the coin split, that failed launch, a fresh split, and a detached start.

## Shape

Testnet-10 only. The Build wallet only. Two lane signers on each of the three public machines, plus two on the synced desk node. The ordered stream is its own process at 4 per second on proton. Depth 2 and in-flight 64 for the lanes. The ordered stream is depth 1. Four connections on each lane signer.

The six public names were still three machines: vector one, muon one, and one machine for proton, electron, quark, and neutrino. The desk node was a fourth machine, synced, kaspad 2.1.0.

Quotes at the arm were desk 100, vector 129, the shared machine 154, and muon 197. None were above 200, so the fee froze at **200 and 300**. The cap stayed 600. Desk miners were 0. The clock offset against time.windows.com was about **+81 ms**. The 3 Oct halt on the older fleet was left in place.

## Score so far

From 2026-10-07T17:48:18.564Z to 2026-10-07T18:35:32.520Z, 2,834 seconds.

Lane signers together: **6,103,249** submit-ok and **6,081,429** seen accepted. That is **2,154** submit per second and **2,146** seen accepted per second. Numeric rejects were 0.

| Signer | Submit per second | Seen accepted per second | Seconds at 0 submit |
|---|---:|---:|---:|
| vector a | 119.2 | 118.8 | 5 |
| vector b | 119.0 | 118.7 | 1 |
| shared a | 801.0 | 798.5 | 1 |
| shared b | 799.2 | 796.6 | 3 |
| muon a | 137.8 | 136.9 | 4 |
| muon b | 137.9 | 137.0 | 2 |
| desk a | 26.9 | 26.8 | 4 |
| desk b | 26.5 | 26.4 | 3 |

The ordered stream submitted **11,240** (4.0 per second) and the 1x lines show **615** seen accepted (0.22 per second). Each second is written twice in that file, once per tier, and the accept count is copied onto both lines. The 615 figure counts each second once. Submit-ok is already split by tier.

This 47-minute lane reading is under the six-hour **2,207** seen accepted. It does not move that figure, and it does not move the 200/300 storm fee.

At 2026-10-07T18:36:09Z the desk sink had **305** transactions and **499,066** of 500,000 compute mass. At 2026-10-07T18:36:15Z the public mempools were vector 21,718, the shared machine 22,814, and muon 26,659. The desk pool was 21,410. All of those are under the 80,000 stop. An api-tn10 health read at 2026-10-07T18:35:56Z timed out. Earlier reads in this window were HTTP 200. One timeout is not a freeze.

Per-transaction logs stayed on the desk. They are not in this repo.

## Close

Stopped at **2026-10-07T18:38:49Z**. The nine signers, the virtual-chain observer, the sink-mass sampler, and the indexer poll were stopped. The 15-minute check and the mempool watcher were cancelled. The desk node was left up, still on testnet-10, port 17210 answering. The 3 Oct halt was left in place. No STOP file was written for the measurement sender.

The last per-second line is 2026-10-07T18:38:39.527Z. From the first kept submit to that line is 3,021 seconds.

Lane signers together: **6,476,277** submit-ok and **6,454,977** seen accepted. That is **2,144** submit per second and **2,137** seen accepted per second.

The ordered stream submitted **11,984** (4.0 per second) and the 1x lines show **660** seen accepted (0.22 per second).

This whole kept window stays under the six-hour **2,207** seen accepted. It does not move that figure, and it does not move the 200/300 storm fee.
