# A2026-10-25

Written 2026-10-25 and frozen the same day as amendment `A2026-10-25` in `configs/phase0.json`. It does not change a Wave 1 result, rule, planning SD, or caliper. It does not change the neighbor gate of 6 or the control gate of at least 1. No ecosystem is dropped. The primary neighbor definition in section 4 and the 34 competitor edges in section 2 are the confirmatory definition. The robustness variant in section 7 is reported beside the primary result and does not replace it.

## 1. How Wave 1 competitor edges were defined

Phase 1 proper, logged 2026-10-11 before the extract, is a hand list. The file is `configs/phase1_universe.json`. The fields are `competitor_tickers` and `competitor_reason`. The list covers Apple, Microsoft, Alphabet, and Tesla only. It cannot generate a Wave 2 edge.

A Wikidata check on 2026-10-12 found no property whose English label is competitor. `competitor_property` is null. P710 was rejected. There is no property to query.

The procedure then used for the rest of Wave 1 is in `reports/phase2_amendment8.md`, section 5, and the edges that passed it are in `kg/phase2_structural_edges.json`. A pair is proposed only where the brand's English Wikipedia article names the rival. The location is logged. The edge sign is −1. The reverse is not asserted. `property_id` is null.

The John Deere–Caterpillar edge logged on 2026-10-21 comes from a 10-K Item 1 Competition section. That is a later source. It was not applied to Wave 2.

## 2. The same procedure on the 16 Wave 2 ecosystems

English Wikipedia was read on 2026-10-25. An edge is kept only when the article names the rival as a competitor, a main rival, or a rival firm. A passing use of the word "competing" is not an edge. No name was invented. An ecosystem whose article does not name a rival has no competitor edge.

| Ticker | Competitor edges | Named rivals |
| --- | ---: | --- |
| DD | 0 | The article does not name a rival. |
| SPG | 0 | The article does not name a rival. |
| BLK | 0 | The article does not name a rival. |
| JNJ | 0 | The article does not name a rival. |
| COP | 0 | The article does not name a rival. |
| BA | 1 | Airbus, named as Boeing's main rival in the paragraph before the Employment numbers. Airbus has no retained ticker. |
| DOW | 0 | "German competitors" and a competing bid from BASF do not name a rival of Dow. |
| ACN | 0 | The 1989 split sentence is about Arthur Andersen and Andersen Consulting. It is not kept. |
| DIS | 0 | The article says Disney is a large theme-park competitor and names no firm. |
| KO | 1 | PepsiCo (PEP). The article calls PepsiCo the company's competitor. |
| BAC | 11 | Lead: JPMorgan Chase (JPM), Citigroup, Wells Fargo (WFC). Section Competition also names Santander, PNC Financial Services (PNC), Ally Financial, Capital One, US Bank, Citizens Financial Group, M&T Bank, and Truist. Citigroup is not given ticker C, because that ticker is ambiguous. US Bank is not U.S. Bancorp. The other six have no retained ticker. JPMorgan Chase is one firm, not two. |
| GILD | 0 | The section "Anticompetitive behavior" names lawsuit co-defendants, not rivals. |
| PSX | 0 | The article does not name a rival. |
| GD | 0 | The article does not name a rival. |
| EA | 3 | Valve and Epic Games, named as direct competitors of EA App, with no retained ticker. Take-Two Interactive (TTWO), named as a rival game company. Steam, the Store, EA App, and PlayStation are products or consoles and are not added. |
| WMT | 18 | Section Competition, "primary competitors include": Target (TGT), Kroger, Harris Teeter, Aldi, Meijer, Trader Joe's, Ingles, Publix, Winn-Dixie, Loblaw Companies, Sobeys, Metro Inc., Giant Tiger, Comercial Mexicana, Soriana, Costco (COST), BJ's Wholesale Club. A separate sentence names Amazon (AMZN) as a competitor. Kroger has no retained ticker (KR is absent). The other unlisted names have no retained ticker. |

Eleven ecosystems have no competitor edge. Five have edges. The total is 34. These edges do not count toward the neighbor gate of 6. The selection criteria already say that no competitor list is invented for that count.

## 3. Structural edges by property

The count is the unique preferred and normal edges in `kg/snapshots/wikidata_2026-10-12/path_edges.json` that touch one of the 15 Wave 2 items present in that snapshot, with both ends having a stored sitelink count of at least 1. Simon Property Group is not in this table. The snapshot still holds the rejected Springer Nature item for SPG, and that item was not used.

1,071 edges.

| Property | Edges | Share |
| --- | ---: | ---: |
| P127 owned by | 408 | 38.1% |
| P1830 owner of | 347 | 32.4% |
| P749 parent organization | 140 | 13.1% |
| P355 subsidiary | 102 | 9.5% |
| P1056 product or material produced | 51 | 4.8% |
| P176 manufacturer | 22 | 2.1% |
| P1716 brand | 1 | 0.1% |
| P169 chief executive officer | 0 in path_edges | The CEO statements sit on the brand item, not in path_edges. They are counted in the neighbor table below. |

Of the 408 P127 edges, 23 (5.6%) have an owner whose instance-of class is investor-type. The classes used are bank, investment bank, commercial bank, retail bank, global systemically important bank, and credit institution, plus a class label containing asset manager, asset management, investment company, investment firm, investment fund, mutual fund, hedge fund, private equity, pension fund, sovereign wealth, or investment management. Holding company is not in this list. Financial services company is not in this list. Central bank is not in this list.

The 23 edges are: Bank of America 14, State Street Corporation 4, J.P. Morgan & Co. 2, Kuwait Investment Authority 1, Morgan Stanley 1, Charles Schwab Corporation 1.

The Vanguard Group is an instance of business, company, and enterprise. BlackRock is an instance of company, business, and public company. Fidelity Investments is an instance of business and enterprise. They are not removed by the instance-of test. The same was found for the Wave 1 holders on 2026-10-19. Vanguard is a direct owner of 13 of these brands, BlackRock of 13, State Street of 4, and Berkshire Hathaway of 3.

## 4. Proposed neighbor definition

A neighbor is another item reached by a preferred or normal statement of one of these properties, with a sitelink count of at least 1:

- P749 parent organization
- P355 subsidiary
- P1716 brand, read as owned brand
- P1056 product or material produced
- P176 manufacturer
- P169 chief executive officer
- P127 owned by, except where the owner is investor-type as defined above

P1830 owner of is not in this list.

The competitor edges in section 2 are added for the news graph. They are not structural neighbors and they do not count toward the gate of 6.

## 5. Gate counts under this definition

Recorded counts are the ones already written in `reports/wave2_candidates.json`. They are not rewritten. The proposed count is a recount on the 2026-10-12 snapshot. BlackRock's recorded neighbor count is 71. This recount is not a claim that the recorded file is wrong, and the file is left as written.

| Ticker | Recorded neighbors | Proposed neighbors | Recorded controls |
| --- | ---: | ---: | ---: |
| DD | 18 | 19 | 8 |
| BLK | 71 | 68 | 3 |
| JNJ | 37 | 35 | 2 |
| COP | 9 | 10 | 6 |
| BA | 36 | 46 | 1 |
| DOW | 6 | 7 | 8 |
| ACN | 6 | 7 | 20 |
| DIS | 232 | 210 | 1 |
| KO | 35 | 34 | 4 |
| BAC | 26 | 14 | 1 |
| GILD | 10 | 10 | 8 |
| PSX | 7 | 8 | 11 |
| GD | 21 | 19 | 5 |
| EA | 36 | 37 | 11 |
| WMT | 32 | 34 | 3 |

Every proposed count is at least 6. A paired recount on the same pool and the same hop rule, once with the recorded properties and once with the proposed properties, gives the same eligible-control count for each of these 15. The proposal does not remove a control. Every recorded control count is at least 1. The absolute recount on a 166-name pool does not reproduce the recorded control counts, so those recorded counts are left as written. Competitor edges are not structural hops, so they do not change the control screen.

Simon Property Group is not in the snapshot. The live item Q2287759 has no P127 statement, so this proposal removes no investor edge from it. Its own statements that meet the sitelink floor are the chief executive officer, David Simon, with 1 sitelink. The subsidiary Mitsubishi Estate Simon has 0 sitelinks and does not count. Two owner-of malls are outside the proposed property list. Incoming neighbors were not re-queried. The logged structural-neighbor count of 111 is not replaced. Simon is not dropped.

No ecosystem falls below a written gate. The gates are not changed.

If the proposal also dropped a P127 edge whose owner is a direct owner of at least 3 of these 15 brands, Accenture would have 5 neighbors and Phillips 66 would have 5. Both would fall below the written gate of 6. BlackRock would have 7 and would still pass. That extra drop is not part of this amendment. The gate stays at 6. Those two ecosystems stay in.

## 6. Alias table

`configs/wave2_gdelt_aliases.json` keeps 30 ecosystems. A brand alias is still accepted only when its mid is one of that brand's mids. Neighbor and competitor titles are a separate list. A title is added only when that item has an English Wikipedia title and a non-deprecated P646 mid. The mid is the item's own mid. A title with no such mid is rejected.

| | Count |
| --- | ---: |
| Titles added | 407 |
| Rejected, no English title | 50 |
| Rejected, no P646 mid | 57 |
| Already covered by a brand title | 16 |
| Titles in each slice query | 442 |
| Mids in each slice query | 438 |

All 128 slice queries in `configs/wave2_gdelt_slices.jsonl` contain those titles and mids. Dates are unchanged. `scripts/phase2_gdelt_wave2.py --self-check` passed and did not start a query.

## 7. Robustness variant

This variant is pre-declared. It is reported beside every Wave 2 primary result. It never replaces the primary result. The gate of 6 applies to the primary definition in section 4 only. An ecosystem below 6 under the variant stays in the 16 and is reported with its variant count.

A primary neighbor is dropped from the variant when either test holds.

1. Multi-ecosystem neighbor. The item is a neighbor, under section 4, of 3 or more of the 16 Wave 2 ecosystems.
2. Generic class. The item is a category rather than a named product, company, person, or brand. The test is the English label. A label with an uppercase letter is a named entity and stays. A label with no uppercase letter stays only when the item is an instance of a chemical entity, a medication, a trademark, a website, or a top-level domain. Those are named products and brands whose labels are lowercase. Every other lowercase label is a generic class. The examples are software, video game, asset management, and truck. Truck is not a neighbor of these 16 under section 4, so it is not in the removal list.

The multi-ecosystem neighbors are The Vanguard Group (13 ecosystems), BlackRock (13), and Berkshire Hathaway (3). BlackRock remains one of the 16 ecosystems. It is dropped only as a neighbor of the others.

The generic classes removed are:

| Item | Ecosystems |
| --- | --- |
| alcoholic beverage | KO |
| asset management | BLK, BAC |
| broadcasting | DIS |
| credit | BAC |
| financial services | BAC |
| gasoline | COP |
| index fund | BLK |
| insurance | BAC |
| medical device | JNJ |
| medication | JNJ |
| music | DIS |
| mutual fund | BLK |
| non-alcoholic beverage | KO |
| plastic | DOW |
| risk management | BLK |
| soft drink | KO |
| software | DIS, EA |
| space technology | BA |
| supermarket | WMT |
| video game (Q56312618) | DIS |
| video game (Q7889) | EA |

Named products with a lowercase label stay. They are the chemical entities calcium chloride, ethylene oxide, lenacapavir, remdesivir, and seladelpar; the medications axicabtagene ciloleucel and bulevirtide; the trademark o.b.; and the named sites and domains babble.com, spoonful.com, .george, and .samsclub.

| Ticker | Primary neighbors | Variant neighbors |
| --- | ---: | ---: |
| DD | 19 | 17 |
| BLK | 68 | 62 |
| JNJ | 35 | 31 |
| COP | 10 | 7 |
| BA | 46 | 43 |
| DOW | 7 | 6 |
| ACN | 7 | 5 |
| DIS | 210 | 204 |
| KO | 34 | 28 |
| BAC | 14 | 7 |
| GILD | 10 | 8 |
| PSX | 8 | 5 |
| GD | 19 | 17 |
| EA | 37 | 35 |
| WMT | 34 | 31 |

Accenture has 5 variant neighbors. Phillips 66 has 5. Both stay in. Simon Property Group's incoming neighborhood was not re-queried, so it has no variant count. It stays in on the logged primary count of 111.

## 8. Wave 2 hypotheses

H2 competitor is tested on the 34 edges in section 2. The 10-pair rule is unchanged. An H2 class, positive or competitor, is tested on an arm and a source only when that class has at least 10 matched pairs. A class below 10 stays in the graph and in H1. It is not rescued by a wider caliper.

The 11 ecosystems with no competitor edge enter H1 and H2 positive only. They do not enter H2 competitor. They are DuPont, Simon Property Group, BlackRock, Johnson & Johnson, ConocoPhillips, Dow, Accenture, Disney, Gilead, Phillips 66, and General Dynamics. Boeing, Coca-Cola, Bank of America, Electronic Arts, and Walmart enter H2 competitor through the 34 edges.
