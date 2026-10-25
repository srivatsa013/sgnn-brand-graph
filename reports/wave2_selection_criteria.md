# Wave 2 ecosystem selection criteria

Written 2026-10-24 before any Wave 2 candidate was counted and before any propagation result was opened. This file is not a freeze. It does not change a result, a rule, a planning SD, or a caliper.

The confirmatory files are not inputs. In particular, Phase 4 effects, p-values, intervals, and decisions, and Phase 5 and Phase 6 errors, are not used.

## Universe

A candidate is an unambiguous ticker in `kg/snapshots/wikidata_2026-10-12/tickers.json` whose chosen Wikidata item has a sitelink count, and which sits in `configs/phase1_universe.json` `control_pool_by_bucket`. The sector is that pre-assigned bucket. Information technology and communication services stay two names on the map. They are one match bucket only when a control is sought.

Excluded before any count:

- a Wave 1 brand ticker
- a ticker that is already a Wave 1 positive node or competitor node
- a ticker in `excluded_from_control_pool`

Wave 1 is the existing 14 ecosystems. The target is 16 more, 30 in total.

## Gates

All of these are required. None is relaxed after the counts are seen.

1. Graph richness. From the 2026-10-12 snapshot, count distinct other items one structural hop from the brand. The properties are the verified set P127, P1830, P1716, P1056, P176, P749, P355, and the CEO property P169. Ranks are preferred and normal. The other item counts only if its stored sitelink count is at least 1. The gate is at least 6. Co-mention is not a structural edge. No competitor list is invented for this count.

2. FNSPID. Distinct days in `eval/results/phase1_fnspid_ticker_daily.csv` are at least 14. Fourteen is the Phase 1 coverage floor.

3. StockTwits. Distinct days in `eval/results/phase1_stocktwits_ticker_daily.csv` with at least one symbol row are at least 14 when the ticker is in that file. A ticker absent from the file is marked `not_stored`. Absence is not a failure and is not a pass of a count this step does not have. No StockTwits file is pulled. A stored count below 14 fails.

4. Controls. Using the frozen rule, a control is ineligible if its Wikidata item is within 2 undirected structural hops of the brand. The remaining controls must lie in the same match bucket. Information technology and communication services use the union. Popularity uses the frozen caliper: the absolute gap in log1p(sitelinks) is at most 1.098612. The mean, SD-ratio, and mention calipers are not applied here, because those series are not stored for this pool. They stay in Phase 4 and are not widened. The gate is at least one control that passes the distance and popularity screens.

5. Sector spread. This is the selection order, not a relaxation of the gates. The 11 buckets stay the names in `configs/sector_taxonomy.json`. While fewer than 16 ecosystems have been taken and an eligible ticker remains, take the next ticker from the bucket with the smallest sum of Wave 1 ecosystems and Wave 2 ecosystems already chosen. A tie follows the bucket order in that file. Inside the bucket the order is: more structural neighbors, then more stored news events, then more FNSPID days, then more eligible controls, then ticker A to Z.

## News events, where a series exists

An event uses the frozen daily rule and nothing else: baseline days −28 through −1, at least 14 observed baseline days, at least 5 mentions on the event day, sample SD with divisor n−1, absolute surprise z at least 2, and 8 refractory days. The series is the stored `cell` table in `data/interim/phase2/series.sqlite` for that ticker or ecosystem name. A missing series is null. It does not fail the ticker and it sorts below a known count. The count is the brand's own event count. It is not a neighbor shift.

## If fewer than 16 pass

Stop. Do not lower the neighbor floor, the coverage floor, or the popularity caliper. Report the shortfall.
