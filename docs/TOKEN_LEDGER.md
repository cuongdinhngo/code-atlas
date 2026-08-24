# Token ledger — code-atlas

One spend row per ticket, required before its PR opens
([`ENGINEERING_RULES.md`](ENGINEERING_RULES.md) R7.2). It lives here rather than in
[`BACKLOG.md`](BACKLOG.md) because it is **tier 2**: a per-ticket retrospective is consulted when
somebody asks what a ticket cost, and is never read to learn a rule — yet in BACKLOG it was charged
to every session, 4,773 tokens of the chain's 49,572 (task 133). Append-only by rule, so it carries
no size ceiling; `tests/test_backlog_bookkeeping.py` reads the table below by heading.

**Is NOT** the per-phase breakdown (→ each task's `tasks/NNN_slug.md` working-doc ledger); not task
status (→ [`BACKLOG.md`](BACKLOG.md)); not rationale (→ [PLAN §19](PLAN.md#19-project-context--decision-log)).

## Token usage

Token spend per task, recorded before its PR is opened
([`ENGINEERING_RULES.md`](ENGINEERING_RULES.md) R7.2); the per-phase breakdown lives in each
task's `tasks/NNN_slug.work.md`
ledger. mango measures **subagent dispatch only**: `unmeasured` = the host surfaced no usage block, and
**main-loop spend is unmeasured unless a fresh/cache figure is given** (`rtk gain` is global and cannot
be attributed to one task, so nothing is invented). `no work doc` = the task skipped the mango
lifecycle. Fresh = input + output + cache-creation; cache reads are billed differently and listed apart.

| # | Tokens | PR |
|---|---|---|
| 001 | 113.6k dispatch (reviewer 70.9k + challenger 42.7k) | [#2](https://github.com/cuongdinhngo/code-atlas/pull/2) |
| 002 | **689.2k fresh** (239.8k out) + 27.12M cache / 164 calls; 0 dispatch | [#4](https://github.com/cuongdinhngo/code-atlas/pull/4) |
| 003 | **638.3k fresh** (223.3k out) + 24.4M cache / 167 calls; + 52.4k dispatch (7.6% — the main loop is the driver) | [#5](https://github.com/cuongdinhngo/code-atlas/pull/5) |
| 004 | 78.1k dispatch (challenger, 27 / 313 s) | [#7](https://github.com/cuongdinhngo/code-atlas/pull/7) |
| 005 | 181.6k dispatch — reviewer 108.9k (38 / 426 s) + challenger 72.7k (27 / 286 s) | [#10](https://github.com/cuongdinhngo/code-atlas/pull/10) |
| 006 | 73.9k dispatch (challenger, 34 / 228 s) | [#13](https://github.com/cuongdinhngo/code-atlas/pull/13) |
| 024 | 0 dispatch; main-loop unmeasured; no work doc | [#14](https://github.com/cuongdinhngo/code-atlas/pull/14) |
| 007 | 111.4k dispatch (challenger, 41 / 380 s) | [#16](https://github.com/cuongdinhngo/code-atlas/pull/16) |
| 009 | 96.3k dispatch (challenger, 30 / 380 s) | [#17](https://github.com/cuongdinhngo/code-atlas/pull/17) |
| 010 | 64.6k dispatch (challenger, 31 / 284 s) | [#18](https://github.com/cuongdinhngo/code-atlas/pull/18) |
| 011 | 2 dispatch, unmeasured | [#19](https://github.com/cuongdinhngo/code-atlas/pull/19) |
| 008 | 4 dispatch, unmeasured | [#20](https://github.com/cuongdinhngo/code-atlas/pull/20) |
| 025 | 4 dispatch unmeasured, + a round-3 ticket-blind challenger **112.6k** (32 / 489 s) — the cell that found the `:col` drift | [#21](https://github.com/cuongdinhngo/code-atlas/pull/21) |
| 012 | 4 dispatch, unmeasured | [#22](https://github.com/cuongdinhngo/code-atlas/pull/22) |
| 013 | 3 dispatch, unmeasured | [#23](https://github.com/cuongdinhngo/code-atlas/pull/23) |
| 014 | 3 dispatch, unmeasured | [#24](https://github.com/cuongdinhngo/code-atlas/pull/24) |
| 015 | 3 dispatch, unmeasured | [#25](https://github.com/cuongdinhngo/code-atlas/pull/25) |
| 016 | 4 dispatch, unmeasured | [#26](https://github.com/cuongdinhngo/code-atlas/pull/26) |
| 017 | 6 dispatch (reviewer ×3 + challenger ×2 + refine), unmeasured | [#27](https://github.com/cuongdinhngo/code-atlas/pull/27) |
| 018 | 3 dispatch, unmeasured | [#28](https://github.com/cuongdinhngo/code-atlas/pull/28) |
| 027 | 4 dispatch, unmeasured | [#30](https://github.com/cuongdinhngo/code-atlas/pull/30) |
| 028 | 2 dispatch, unmeasured | [#31](https://github.com/cuongdinhngo/code-atlas/pull/31) |
| 029 | 5 dispatch, unmeasured | [#32](https://github.com/cuongdinhngo/code-atlas/pull/32) |
| 030 | 5 dispatch, unmeasured | [#33](https://github.com/cuongdinhngo/code-atlas/pull/33) |
| 031 | 3 dispatch, unmeasured | [#34](https://github.com/cuongdinhngo/code-atlas/pull/34) |
| 032 | 0 dispatch; main-loop unmeasured | [#36](https://github.com/cuongdinhngo/code-atlas/pull/36) |
| 034 | 0 dispatch; main-loop unmeasured; no work doc | [#37](https://github.com/cuongdinhngo/code-atlas/pull/37) |
| 033 | 3 dispatch, unmeasured | [#40](https://github.com/cuongdinhngo/code-atlas/pull/40) |
| 035 | 4 dispatch, unmeasured | [#41](https://github.com/cuongdinhngo/code-atlas/pull/41) |
| 036 | 4 dispatch, unmeasured | [#42](https://github.com/cuongdinhngo/code-atlas/pull/42) |
| 037 | **242.7k dispatch, all measured** — challenger 61.9k (32 / 336 s) + reviewer 106.5k (42 / 595 s) + reviewer r2 74.2k (39 / 433 s) | [#43](https://github.com/cuongdinhngo/code-atlas/pull/43) |
| 038 | 4 dispatch, unmeasured | [#44](https://github.com/cuongdinhngo/code-atlas/pull/44) |
| 039 | 5 dispatch, unmeasured | [#45](https://github.com/cuongdinhngo/code-atlas/pull/45) |
| 040 | 4 dispatch, unmeasured | [#46](https://github.com/cuongdinhngo/code-atlas/pull/46) |
| 041 | 4 dispatch, unmeasured | [#47](https://github.com/cuongdinhngo/code-atlas/pull/47) |
| 042 | **134.4k dispatch, measured** — reviewer 85.6k (22 / 266 s) + challenger 48.8k (25 / 234 s) | [#48](https://github.com/cuongdinhngo/code-atlas/pull/48) |
| 043 | **150.7k dispatch, measured** — reviewer 86.4k (28 / 326 s) + challenger 64.3k (28 / 285 s) | [#49](https://github.com/cuongdinhngo/code-atlas/pull/49) |
| 044 | 0 dispatch; main-loop unmeasured; no work doc | [#50](https://github.com/cuongdinhngo/code-atlas/pull/50) |
| 045 | 0 dispatch; main-loop unmeasured; no work doc | [#51](https://github.com/cuongdinhngo/code-atlas/pull/51) |
| 046 | 0 dispatch; main-loop unmeasured; no work doc | [#52](https://github.com/cuongdinhngo/code-atlas/pull/52) |
| 047 | 0 dispatch; main-loop unmeasured | [#56](https://github.com/cuongdinhngo/code-atlas/pull/56) |
| 048 | 0 dispatch; main-loop unmeasured | [#55](https://github.com/cuongdinhngo/code-atlas/pull/55) |
| 049 | 0 dispatch; main-loop unmeasured | [#57](https://github.com/cuongdinhngo/code-atlas/pull/57) |
| 050 | 0 dispatch; main-loop unmeasured | [#58](https://github.com/cuongdinhngo/code-atlas/pull/58) |
| 051 | 0 dispatch; main-loop unmeasured | [#60](https://github.com/cuongdinhngo/code-atlas/pull/60) |
| — | Ticket-writing for 051: **39.5k fresh** (13.5k out) + 3.3M cache / 23 calls | [#59](https://github.com/cuongdinhngo/code-atlas/pull/59) |
| — | Ticket-writing + the field retro that produced 047–049: **45.6k fresh** / 28 calls for the tickets, plus **1.84M fresh** (503.0k out) + 122.2M cache / 576 calls for the retro, the 049 design measurement and everything before the first commit — not attributable to one task. | — |
| — | Ticket-writing for 052 + 053: **463.1k fresh** (58.7k out) + 6.7M cache / 72 calls, one inseparable pass. **Recorded late** | [#54](https://github.com/cuongdinhngo/code-atlas/pull/54) |
| — | Ticket-writing for 054: **356.0k fresh** (139.5k out) + 17.2M cache / 104 calls — **also produced the 055–061 tickets** | [#61](https://github.com/cuongdinhngo/code-atlas/pull/61) |
| — | Ticket-writing for 055–061: **30.2k fresh** (8.0k out) + 2.6M cache / 11 calls — tail only; honest total with the row above is **386.2k fresh / 115 calls**. | [#62](https://github.com/cuongdinhngo/code-atlas/pull/62) |
| — | Ticket-writing for 064–070: **384.8k fresh** (117.1k out) + 11.8M cache / 136 calls — also the contract-v5 rebuild, the round-3 retro, and reproducing every claim before ticketing. | [#77](https://github.com/cuongdinhngo/code-atlas/pull/77) |
| — | Ticket-writing for 071–074 + the memory/concurrency run: **222.0k fresh** (58.3k out) + 5.9M cache / 56 calls. | [#78](https://github.com/cuongdinhngo/code-atlas/pull/78) |
| — | The founding-premise benchmark + the PLAN §19 decision: **549.6k fresh** (105.4k out) + 7.6M cache / 100 calls. | [#62](https://github.com/cuongdinhngo/code-atlas/pull/62) |
| 059 | 2 dispatch, unmeasured | [#63](https://github.com/cuongdinhngo/code-atlas/pull/63) |
| 055 | 5 dispatch, unmeasured | [#64](https://github.com/cuongdinhngo/code-atlas/pull/64) |
| 054 | 4 dispatch, unmeasured | [#65](https://github.com/cuongdinhngo/code-atlas/pull/65) |
| 056 | 3 dispatch, unmeasured | [#66](https://github.com/cuongdinhngo/code-atlas/pull/66) |
| 057 | 4 dispatch, unmeasured | [#67](https://github.com/cuongdinhngo/code-atlas/pull/67) |
| 058 | 3 dispatch, unmeasured | [#68](https://github.com/cuongdinhngo/code-atlas/pull/68) |
| 060 | 3 dispatch, unmeasured | [#69](https://github.com/cuongdinhngo/code-atlas/pull/69) |
| 052 | 5 dispatch (review rounds 1–2), unmeasured | [#70](https://github.com/cuongdinhngo/code-atlas/pull/70) |
| 053 | 5 dispatch (review rounds 1–2), unmeasured | [#71](https://github.com/cuongdinhngo/code-atlas/pull/71) |
| 061 | 5 dispatch (review rounds 1–2), unmeasured | [#72](https://github.com/cuongdinhngo/code-atlas/pull/72) |
| 062 | 6 dispatch, unmeasured | [#73](https://github.com/cuongdinhngo/code-atlas/pull/73) |
| 063 | 6 dispatch, unmeasured | [#75](https://github.com/cuongdinhngo/code-atlas/pull/75) |
| 064 | 0 dispatch (review waived); main-loop unmeasured | [#79](https://github.com/cuongdinhngo/code-atlas/pull/79), [#80](https://github.com/cuongdinhngo/code-atlas/pull/80) |
| 065 | 2 dispatch, unmeasured. Post-PR review fixed a red `mypy` gate + the reason missing on `both` | [#81](https://github.com/cuongdinhngo/code-atlas/pull/81) |
| 073 | 2 dispatch, unmeasured. Post-PR review found miss-repair firing on an empty *page* | [#82](https://github.com/cuongdinhngo/code-atlas/pull/82) |
| — | CI drift audit (no ticket, no work doc): 0 dispatch — three workflows re-read, one benchmark re-measured, full `pytest` | [#83](https://github.com/cuongdinhngo/code-atlas/pull/83) |
| 071 | 2 dispatch, unmeasured. | [#84](https://github.com/cuongdinhngo/code-atlas/pull/84) |
| 068 | 2 dispatch, unmeasured. Post-PR review removed two dead reconcile exemptions + an absence-proving test | [#85](https://github.com/cuongdinhngo/code-atlas/pull/85) |
| 067 | 0 dispatch (review waived); main-loop unmeasured | [#86](https://github.com/cuongdinhngo/code-atlas/pull/86) |
| 066 | 0 dispatch (review waived); main-loop unmeasured | [#87](https://github.com/cuongdinhngo/code-atlas/pull/87) |
| 072 | 0 dispatch (review waived); main-loop unmeasured | [#89](https://github.com/cuongdinhngo/code-atlas/pull/89) |
| 070 | **78.5k dispatch** — 1 analysis Explore (17 / 126 s); review waived | [#91](https://github.com/cuongdinhngo/code-atlas/pull/91) |
| 069 | **113.7k dispatch** — analysis Explore 88.3k (40 / 227 s) + an execute blind-reader routing exercise 25.3k; review waived | [#92](https://github.com/cuongdinhngo/code-atlas/pull/92) |
| 074 | 0 dispatch; main-loop unmeasured | [#93](https://github.com/cuongdinhngo/code-atlas/pull/93) |
| 075 | 0 dispatch (review waived); main-loop unmeasured | [#94](https://github.com/cuongdinhngo/code-atlas/pull/94) |
| 076 | 0 dispatch; main-loop unmeasured | [#94](https://github.com/cuongdinhngo/code-atlas/pull/94) |
| 077 | 2 dispatch, unmeasured (explore + exposure-checker); review waived | [#96](https://github.com/cuongdinhngo/code-atlas/pull/96) |
| 078 | 2 dispatch, unmeasured (explore + exposure-checker); review waived | [#97](https://github.com/cuongdinhngo/code-atlas/pull/97) |
| 079 | 0 dispatch (review waived); main-loop unmeasured | [#98](https://github.com/cuongdinhngo/code-atlas/pull/98) |
| 082 | 1 dispatch — refine exposure-checker **50.5k** (9 tool-uses, 154 s); review waived. Docker runs for delta-green (full gate **1134 passed**) | [#99](https://github.com/cuongdinhngo/code-atlas/pull/99) |
| 081 | 1 dispatch — refine exposure-checker **60.4k** (17 tool-uses, 194 s); review waived. Docker runs for delta-green (full gate **1137 passed**) | [#100](https://github.com/cuongdinhngo/code-atlas/pull/100) |
| 080 | 1 dispatch — refine exposure-checker **57.8k** (8 tool-uses, 187 s); review waived. | [#101](https://github.com/cuongdinhngo/code-atlas/pull/101) |
| 092 | 1 dispatch — refine exposure-checker unmeasured (blocking retrieval); review waived at solve time, then done on the PR (0 dispatch, in-session). | [#102](https://github.com/cuongdinhngo/code-atlas/pull/102) |
| 093 | 1 dispatch — `/code-review` on the PR **61.7k** (20 tool-uses, 205 s); refine skipped (0 unresolved product-decisions), review waived at solve time then run on the PR. | [#103](https://github.com/cuongdinhngo/code-atlas/pull/103) |
| 095 | 1 dispatch — refine exposure-checker unmeasured (host does not surface usage); review waived at solve time. | [#105](https://github.com/cuongdinhngo/code-atlas/pull/105) |
| 097 | 1 dispatch — refine exposure-checker unmeasured (host does not surface usage); review waived at solve time. | [#107](https://github.com/cuongdinhngo/code-atlas/pull/107) |
| 094 | 1 dispatch — refine exposure-checker unmeasured (host does not surface usage); review waived at solve time, then run on the PR (0 dispatch, in-session — caught `self`/`static`/`parent``::class` emitting `\self`). | [#108](https://github.com/cuongdinhngo/code-atlas/pull/108) |
| 096 | 0 dispatch (review waived); main-loop unmeasured | [#110](https://github.com/cuongdinhngo/code-atlas/pull/110) |
| 099 | 0 dispatch (review waived); main-loop unmeasured | [#111](https://github.com/cuongdinhngo/code-atlas/pull/111) |
| — | CI red on `main` after #108: profiler wall-tolerance floor. | [#109](https://github.com/cuongdinhngo/code-atlas/pull/109) |
| 100 | **296.0k dispatch, all measured** — `mango:reviewer` r1 134.9k (54 tool-uses, 649 s) + r2 verify 161.1k (16 / 272 s); main-loop unmeasured. | [#114](https://github.com/cuongdinhngo/code-atlas/pull/114) |
| 101 | **139.2k dispatch, all measured**; main-loop unmeasured. | [#116](https://github.com/cuongdinhngo/code-atlas/pull/116) |
| 102 | **89.4k dispatch, all measured**; main-loop unmeasured. | [#117](https://github.com/cuongdinhngo/code-atlas/pull/117) |
| — | Ticket-writing for 102: 0 dispatch; the defect was measured during 100, not by a separate run | [#115](https://github.com/cuongdinhngo/code-atlas/pull/115) |
| — | Field retro round 4 + ticket-writing for 075–082: 0 dispatch. | — |
| 083 | **65.4k dispatch, measured** — `mango:reviewer` r1 65.4k (30 tool-uses, 233 s) → LGTM, no findings; main-loop unmeasured. | [#120](https://github.com/cuongdinhngo/code-atlas/pull/120) |
| 084 | **124.4k dispatch, measured**; main-loop unmeasured. | [#121](https://github.com/cuongdinhngo/code-atlas/pull/121) |
| 103 | **175.4k dispatch, all measured**; main-loop unmeasured. | [#122](https://github.com/cuongdinhngo/code-atlas/pull/122) |
| 104 | **91.8k dispatch, measured**; main-loop unmeasured. AC2 closed later at 0 dispatch by three pinned-repo `layer_report.py` runs (#159). | [#123](https://github.com/cuongdinhngo/code-atlas/pull/123) |
| 085 | **136.5k dispatch, measured**; main-loop unmeasured. | [#124](https://github.com/cuongdinhngo/code-atlas/pull/124) |
| 086 | 0 dispatch (review waived); main-loop unmeasured | [#125](https://github.com/cuongdinhngo/code-atlas/pull/125) |
| 087 | 0 dispatch (review waived); main-loop unmeasured | [#126](https://github.com/cuongdinhngo/code-atlas/pull/126) |
| 088 | 0 dispatch (review waived); main-loop unmeasured | [#127](https://github.com/cuongdinhngo/code-atlas/pull/127) |
| 089 | 0 dispatch (review waived); main-loop unmeasured | [#128](https://github.com/cuongdinhngo/code-atlas/pull/128) |
| 090 | 0 dispatch (review waived); main-loop unmeasured | [#129](https://github.com/cuongdinhngo/code-atlas/pull/129) |
| 105 | 0 dispatch (review waived); main-loop unmeasured | [#131](https://github.com/cuongdinhngo/code-atlas/pull/131) |
| 091 | 0 dispatch (review waived); main-loop unmeasured | [#130](https://github.com/cuongdinhngo/code-atlas/pull/130) |
| 106 | 0 dispatch (review waived); main-loop unmeasured | [#132](https://github.com/cuongdinhngo/code-atlas/pull/132) |
| 107 | 0 dispatch (review waived); main-loop unmeasured | [#133](https://github.com/cuongdinhngo/code-atlas/pull/133) |
| 108 | 0 dispatch (review waived); main-loop unmeasured | [#135](https://github.com/cuongdinhngo/code-atlas/pull/135) |
| 110 | **95.3k dispatch, measured**; main-loop unmeasured. | [#137](https://github.com/cuongdinhngo/code-atlas/pull/137) |
| 109 | 0 dispatch (review waived); main-loop unmeasured | [#136](https://github.com/cuongdinhngo/code-atlas/pull/136) |
| 111 | **61.6k dispatch, measured**; main-loop unmeasured. | [#138](https://github.com/cuongdinhngo/code-atlas/pull/138) |
| 112 | **116.0k dispatch, measured**; main-loop unmeasured. | [#139](https://github.com/cuongdinhngo/code-atlas/pull/139) |
| 113 | 0 dispatch (review waived); main-loop unmeasured | [#140](https://github.com/cuongdinhngo/code-atlas/pull/140) |
| 114 | 0 dispatch (review waived); main-loop unmeasured | [#141](https://github.com/cuongdinhngo/code-atlas/pull/141) |
| 115 | 0 dispatch (review waived); main-loop unmeasured | [#142](https://github.com/cuongdinhngo/code-atlas/pull/142) |
| 116 | 0 dispatch (review waived); main-loop unmeasured | [#143](https://github.com/cuongdinhngo/code-atlas/pull/143) |
| 117 | 0 dispatch (review waived); main-loop unmeasured | [#144](https://github.com/cuongdinhngo/code-atlas/pull/144) |
| — | **Docs-truth sweep + four tickets authored (118 · 119 · 120 · 121).** 0 dispatch — main-loop only, **unmeasured** (the host surfaces no usage block); no mango lifecycle, so `no work doc`. | [#145](https://github.com/cuongdinhngo/code-atlas/pull/145) |
| — | **Round-6 retro triage + four tickets authored (122 · 123 · 124 · 125).** 0 dispatch — main-loop only, **unmeasured** (no usage block surfaced); no mango lifecycle, so `no work doc`. | [#146](https://github.com/cuongdinhngo/code-atlas/pull/146) |
| 122 | 0 dispatch (review waived); main-loop unmeasured | [#147](https://github.com/cuongdinhngo/code-atlas/pull/147) |
| 123 | 0 dispatch (review waived); main-loop unmeasured | [#148](https://github.com/cuongdinhngo/code-atlas/pull/148) |
| 124 | 0 dispatch (review waived); main-loop unmeasured | [#149](https://github.com/cuongdinhngo/code-atlas/pull/149) |
| 125 | 0 dispatch (review waived); main-loop unmeasured | [#150](https://github.com/cuongdinhngo/code-atlas/pull/150) |
| 126 | 0 dispatch (review waived); main-loop unmeasured | [#151](https://github.com/cuongdinhngo/code-atlas/pull/151) |
| 127 | 0 dispatch (review waived); main-loop unmeasured | [#151](https://github.com/cuongdinhngo/code-atlas/pull/151) |
| 121 | 0 dispatch; main-loop unmeasured | [#152](https://github.com/cuongdinhngo/code-atlas/pull/152) |
| 119 | 0 dispatch; main-loop unmeasured | [#151](https://github.com/cuongdinhngo/code-atlas/pull/151) |
| 132 | 0 dispatch; main-loop unmeasured | [#153](https://github.com/cuongdinhngo/code-atlas/pull/153) |
| 129 | 0 dispatch; main-loop unmeasured | [#154](https://github.com/cuongdinhngo/code-atlas/pull/154) |
| 134 | 0 dispatch; main-loop unmeasured | [#155](https://github.com/cuongdinhngo/code-atlas/pull/155) |
| 135 | 0 dispatch (no work doc); main-loop unmeasured. Two sample-tier clones (`symfony/demo`) and one pre-change re-run produced the before/after pair | [#156](https://github.com/cuongdinhngo/code-atlas/pull/156) |
| 136 | 0 dispatch (no work doc); main-loop unmeasured. Three pinned clones indexed twice for the determinism check; also produced 137 | [#157](https://github.com/cuongdinhngo/code-atlas/pull/157) |
| 133 | 0 dispatch (review + challenger waived by the run's args); main-loop unmeasured (host surfaces no usage block) | [#158](https://github.com/cuongdinhngo/code-atlas/pull/158) |
| 120 | 0 dispatch (review + challenger waived by the run's args); main-loop unmeasured (host surfaces no usage block) | [#160](https://github.com/cuongdinhngo/code-atlas/pull/160) |
| 118 | 0 dispatch (review + challenger waived by the run's args); main-loop unmeasured (host surfaces no usage block) | [#163](https://github.com/cuongdinhngo/code-atlas/pull/163) |
| 130 | 0 dispatch (review + challenger waived by the run's args); main-loop unmeasured (host surfaces no usage block) | [#164](https://github.com/cuongdinhngo/code-atlas/pull/164) |
| 131 | 0 dispatch (review + challenger waived by the run's args); main-loop unmeasured (host surfaces no usage block) | [#165](https://github.com/cuongdinhngo/code-atlas/pull/165) |
| 138 | 0 dispatch (review + challenger waived by the run's args); main-loop unmeasured (host surfaces no usage block); AC7 deferred to 142 | [#166](https://github.com/cuongdinhngo/code-atlas/pull/166) |
| 139 | 0 dispatch (review + challenger waived by the run's args); main-loop unmeasured (host surfaces no usage block); AC6 deferred to 142 | [#167](https://github.com/cuongdinhngo/code-atlas/pull/167) |
| 143 | 0 dispatch (review + challenger waived by the run's args); main-loop unmeasured (host surfaces no usage block) | [#168](https://github.com/cuongdinhngo/code-atlas/pull/168) |
| 144 | 0 dispatch (review + challenger waived by the run's args); main-loop unmeasured (host surfaces no usage block) | [#169](https://github.com/cuongdinhngo/code-atlas/pull/169) |
| 145 | 0 dispatch (review + challenger waived by the run's args); main-loop unmeasured (host surfaces no usage block); Phase A only | [#170](https://github.com/cuongdinhngo/code-atlas/pull/170) |
| 146 | 0 dispatch; main-loop unmeasured (host surfaces no usage block); found while reviewing #170 | [#171](https://github.com/cuongdinhngo/code-atlas/pull/171) |
| 137 | 0 dispatch; main-loop unmeasured (host surfaces no usage block); review/challenger waived. Three measured commits plus a baseline worktree at 2455835 to prove recall | [#172](https://github.com/cuongdinhngo/code-atlas/pull/172) |
| 140 | 0 dispatch; main-loop unmeasured (host surfaces no usage block); review/challenger waived. Benchmark run on the pins, not only the fixture, which is what surfaced the empty-module-table case | [#173](https://github.com/cuongdinhngo/code-atlas/pull/173) |

**How 047–049 were measured.** One autonomous session, no per-task transcript: each row is the API
calls between the previous commit and that task's own commit. The approximation runs one way — work
interleaved across tasks lands in whichever segment it finished in (049 is the known case).

