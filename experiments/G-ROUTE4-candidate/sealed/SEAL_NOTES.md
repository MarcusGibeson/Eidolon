# G-ROUTE4 seal notes

**What this is.** The single G-ROUTE4 seal commit (obligation O1): the complete authored corpus of 584 fixtures
(A′ 80 and B′ 305 main, 80 A′ and 119 B′ reserve), gold and rationales, the authoring and provenance ledger, the
frozen O2 adjudicator configuration, the O3 identifier decision and gate, the committed name stream, and a manifest
of every pinned digest. It is built by `build_seal.py` from staging checkpoint
`dd8193bfcf1db05c752635dc4f8911a58098c97b` with the prepared, tested seal layout. It contains no runtime outputs,
model responses or adjudication results. No model or adjudicator was contacted before or during the seal.

**Parent and placement.** The seal's parent is the frozen blueprint commit
`1156d0645b1b113b91c65e4a485b7f75ffa10061`. By operator instruction (2026-09-29) the seal is pushed to the branch
`g-route4/seal` and `main` is not moved. The frozen `seal_requirement` ("the single commit on main whose parent is
the commit adding this manifest") is met when `main` is fast-forwarded to this commit or its descendants; a
fast-forward does not change the seal id, and no other commit may be placed on `main` with that parent.
Disclosed: the authoring branch `g-route4/authoring-staging` begins with commit
`8d890b2fff9de7616e98cab71665025909647d21`, whose parent is also `1156d06`; it is authoring-only and never merged.

**Only one seal.** This seal commit id is recorded when it is pushed; any later re-seal is refused. If one ever
happens, both samples are disclosed and their union is audited.

**O1 audit sample (runbook).** Computed only after this commit is pushed to `origin`, by the frozen procedure
`experiments/G-ROUTE4-candidate/blueprint/audit_sample.py` (sha256
`8e5afc8478c913150fd9d4ac9564a829ae857e74d005ca4371d2b76937767524`, self-test
`75af7d1ad5d785b40c1a41f15e4d23fa7e987715530e8d9b64f4fec5a4b398c9`) with this commit's id, over the frozen
blueprint's B′ main cells: 38 fixtures. It is committed as a separate commit after the seal and before the first
adjudication session, with the local reflog around the seal disclosed.

**Carried note N4 (checked at SEAL), clarified.** For sampled fixtures that the first adjudicator agrees with, the
two further blind adjudicators always run, and the operator is involved only on disagreement. Any disagreement within
a sampled cell is also reported.

**After the seal.** Gold changes only through a recorded fix, with re-adjudication from scratch (design, gold
adjudication steps 3 and 7). The O2 configuration changes only by a recorded operator decision, after which every
fixture is re-adjudicated from scratch.
