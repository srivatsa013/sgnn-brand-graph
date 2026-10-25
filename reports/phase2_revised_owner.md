# Revised owner rule, brands, and the GDELT pilot

Logged 2026-10-20, before the recount. The full 128-slice rerun was not started. Phase 3 scoring was not started.

## Owner rule

An owner link is dropped when the owner holds a non-deprecated ownership statement on at least 25 percent of the 206 retained tickers. That is at least 52 tickers. The only owner is The Vanguard Group, Q849363, 53 tickers, share 0.257282. BlackRock holds 50, share 0.242718, and stays. The list is `configs/amendment8_revised_owners.json`. The strict graph keeps every owner link.

## Pairs, on the 2026-10-20 pool

Returned names are in the pool. The new brand tickers are out. Counts are usable pairs, not effects.

| Graph | News H1 / events | News positive | News competitor | Social H1 / events | Social positive | Social competitor |
| --- | --- | --- | --- | --- | --- | --- |
| Strict | 28 / 20 | 6 | 22 | 179 / 133 | 28 | 151 |
| Revised | 28 / 20 | 6 | 22 | 193 / 143 | 28 | 165 |

Eligible controls, strict then revised: Apple 22 then 24, Microsoft 22 then 23, Alphabet 8 then 8, Tesla 17 then 17. The revision adds AKAM and NVDA for Apple, and NVDA for Microsoft. AKAM is the one of those three with an Arm A series. AKAM stays inside Microsoft's two-hop set on a path that is not Vanguard.

Positive funnel, both graphs. Columns are events, both windows before brand exclusion, both windows after exclusion, and a control inside the calipers.

| Brand | News | Social |
| --- | --- | --- |
| Apple | 14 / 14 / 0 / 0 | 171 / 96 / 35 / 0 |
| Microsoft | 5 / 5 / 1 / 0 | 110 / 29 / 16 / 2 |
| Alphabet | 15 / 15 / 5 / 0 | 142 / 93 / 93 / 0 |

Alphabet social, revised and strict: 338 comparisons, mean 145, SD 216, mention 76, popularity 0. Eligible communication controls are 8.

## TweetsKB 5 percent placebo

Seed 3. Alphabet has 0 eligible dates, so the draw uses Google. The revised graph:

| Series | Dates | In the 5% file | Eligible but absent | Comparisons | 14-day baselines | Dates with no baseline | Mean | SD | Mention | Popularity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Apple | 20 | 14 | 10 | 280 | 8 | 13 | 8 | 5 | 2 | 0 |
| Microsoft | 20 | 13 | 10 | 260 | 6 | 15 | 6 | 4 | 0 | 0 |
| Google | 20 | 8 | 0 | 160 | 20 | 7 | 20 | 0 | 0 | 0 |

The absent names are the returned semiconductor tickers, including NVDA. They are eligible on the graph and are not in the 5 percent control file, so they are not compared. No comparison passes the popularity caliper.

## Brands

Ecosystems: 13. Brand nodes: 13. Competitor edges: 27. NextEra Energy is not an ecosystem.

John Deere's 10-K for the year ended 2025-11-02, filed 2025-12-18, names Caterpillar in Item 1 Competition. CAT is retained. No other named rival is a retained ticker. The New York Times Company's 10-K for the year ended 2025-12-31, filed 2026-02-27, names Apple, Alphabet, Meta Platforms, and Microsoft. Those four are retained. The Wall Street Journal and ESPN are named and are not retained tickers. No edge was added for Deere or the Times.

## GDELT pilot

Account `srivatsa.singaraju2023@vitstudent.ac.in`, project `sgnn-csp-2`. The token worked.

| Gate | Result |
| --- | --- |
| (a) Every dry run at most 10 GB | Pass. Largest is 3,333,846,320 bytes. |
| (b) Projected total plus 50 GB inside this month's remainder | Pass. October billed bytes are 435,353,026,560. Remainder of 1 TB is 564,646,973,440. |
| (c) Eighteen large names, plus Cisco, on at least 2 of 3 days | Fail. Cisco is not on the frozen allow-list and has rows on 0 days. The other eighteen have rows on 2016-11-14 and 2020-03-16. |
| (d) Arm B study nodes and aliases | Pass on the days they existed. Apple, Microsoft, Alphabet, iPhone, MacBook, Windows, Azure, YouTube, and Android return on both 2016-11-14 and 2020-03-16. LinkedIn is on neither day in the earlier scan. |
| (e) Result fits with 3 GB spare | Not reached. Free space at the stop was 14 GB. The loop was not started. |

`geg_gcnlapi` processes 0 bytes for 2025-06-16. The stored extract's previous slice ends 2025-06-12 and the next rows begin 2025-07-02.

Zero-row entities on the pilot, 20 of 260. No title and no mid, so they cannot match: PINS, ADP, FOXA, NWSA, C, BMY, MRK, HAL, Garmin Ltd. A title or a mid, and still no row on either populated day: NIO, RTX, UNP, EQR, EXR, SBAC, SPG, VICI, Lucid Motors, Stellantis, KLA Corporation.

## Not started

TweetsKB: not started. The stream test and the 2016-11 through 2020-12 download wait on the rerun, which did not start.

Phase 3A hand-label sample: not started. Phase 3 scoring: not started.

The series rebuild, the precision audit, coverage, the proposed GDELT planning SD, and the Arm B feasibility call wait on the full rerun.
