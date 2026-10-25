# Scale-up proposal

Date: 2026-10-14. Research only. No new brand was added to the graph. No corpus was downloaded. The four current ecosystems stay the deep ones. This expands the pre-registered "2–3 ecosystems" and is waiting for the guide. The log entry is in `DECISIONS_LOG.md` on this date.

## Twelve proposed brands

Each name is still outside the two-hop Wikidata neighborhood of the current study nodes, so it is not already tied to Apple, Microsoft, Alphabet, or Tesla. Disney, Starbucks, Home Depot, Coca-Cola, Walmart, and Visa are already inside that neighborhood, so they are not proposed as separate ecosystems. Nike is outside it and is proposed.

GDELT scored days were not measured. A scan of those names is the same extract as Part 1 and does not fit this month. Arm A days are scored days already in `series.sqlite`. "Dense" means days that themselves have at least 14 scored documents. TweetsKB was queried only for the information-technology and communication control lists, so most of these brands have no TweetsKB count yet.

| Brand | Wikidata | Sector | Arm A news days (dense) | Arm A social days (dense) | Competitors to confirm |
| --- | --- | --- | --- | --- | --- |
| Nike | Q483915 | discretionary | 2,736 (33) | 3,666 (776) | No second footwear name is in the clean pool. |
| Chipotle | Q465751 | discretionary | 2,495 (60) | 4,029 (1,064) | Darden Q742196 |
| Lowe's | Q1373493 | discretionary | 1,241 (29) | 2,691 (150) | Home Depot is inside the two-hop set, so it is not the proposed competitor. |
| T-Mobile US | Q3511885 | communication | 2,202 (7) | 2,703 (183) | AT&T and Verizon are inside the two-hop set. Dish Q1199757 is the clean-pool candidate. TweetsKB days already counted: 990. |
| New York Times Company | Q2529982 | communication | 923 (0) | 787 (5) | No direct peer in the clean pool. TweetsKB days already counted: 16. |
| Hershey | Q1056637 | staples | 847 (5) | 1,525 (6) | General Mills Q629998, Kellanova Q856897 |
| Colgate-Palmolive | Q609466 | staples | 2,048 (13) | 4,043 (1,296) | Clorox Q910368, Kimberly-Clark Q1741634 |
| Mastercard | Q489921 | financials | 1,123 (6) | 3,629 (418) | Visa is inside the two-hop set. |
| Chevron | Q319642 | energy | 2,103 (34) | 3,312 (471) | Marathon Petroleum Q458363, Valero Q1283291. Exxon is inside the two-hop set. |
| NextEra Energy | Q967868 | utilities | 2,649 (5) | 1,861 (55) | Duke Energy Q1264404, Southern Company Q2304693 |
| John Deere | Q496302 | industrials | 2,135 (35) | 2,606 (98) | Caterpillar is inside the two-hop set. |
| Eli Lilly | Q632240 | healthcare | 1,393 (11) | 2,585 (124) | Amgen Q470517, Vertex Q2744099, if you accept them as peers. |

That is 12 brands and 8 sectors. With the existing four, the graph would hold 16 brands. Products and subsidiaries are not listed here. Each one still needs the same dated Wikidata ownership check used for LinkedIn. Competitor edges are not added until you confirm them.

## Control pool after the current two-hop exclusion

These counts are the pool that remains before any proposed brand is removed. Adding a brand later removes that ticker and its two-hop neighbors from the controls.

| Sector | Remaining | Remaining tickers |
| --- | --- | --- |
| Information technology | 14 | ADP, ADSK, BR, CDNS, CTSH, EPAM, FFIV, INTU, IT, JKHY, MSI, NTAP, PAYX, SNPS |
| Communication | 10 | CMCSA, DISH, FOXA, IPG, LUMN, NWSA, NYT, OMC, SIRI, TMUS |
| Consumer discretionary | 12 | CCL, CMG, DRI, EXPE, HLT, LOW, LVS, MAR, NKE, ROST, TGT, TJX |
| Financials | 7 | CB, MA, MET, MMC, PGR, SCHW, SPGI |
| Healthcare | 10 | AMGN, BMY, ISRG, LLY, MDT, SYK, TMO, UNH, VRTX, ZTS |
| Energy | 12 | BKR, CVX, DVN, EOG, EPD, KMI, MPC, OKE, OXY, SLB, VLO, WMB |
| Utilities | 16 | AEE, AEP, AWK, D, DUK, ED, EIX, ES, EXC, NEE, PCG, PEG, SO, SRE, WEC, XEL |
| Industrials | 10 | CSX, DE, EMR, ETN, HON, ITW, NSC, PH, UNP, WM |
| Consumer staples | 9 | CHD, CL, CLX, GIS, HSY, K, KMB, MO, SYY |
| Materials | 13 | APD, BALL, DOW, ECL, FCX, IP, LIN, MLM, NEM, NUE, PPG, SHW, VMC |
| Real estate | 14 | AMT, AVB, CCI, DLR, EQIX, EQR, EXR, O, PLD, PSA, SBAC, SPG, VICI, WELL |

ADP, BMY, FOXA, and NWSA stay ineligible as ambiguous tickers.

## Staging

Arm A daily cells for these tickers are already stored. After you confirm the list, the local work is the competitor edges and the ownership check, on the order of a few days. TweetsKB aggregates for the 12 brands and their competitors are SPARQL only, about a day of endpoint time. GDELT is one scripted day in November, on the reset quota, using the single scan below. The four deep ecosystems are not rebuilt. If the list is confirmed in October, the semester can absorb the November extract and the edge confirmation without a new collection project.

## Fuller TweetsKB

Parts 1–9 are the Zenodo release, CC BY 4.0, about 342 GiB compressed, February 2013 through December 2020. They do not fit on the disk. A stream can keep one monthly file, write the per-entity daily aggregate and the per-tweet entity list, and delete the file. Peak disk is one file, a few gigabytes, which fits in the free 18 GB. At a sustained 10 MB/s the 342 GiB take about 10 hours. At 2 MB/s they take about two days. That is an estimate from the size, not a timed download.

Parts 10–12 are on GESIS, not the CC BY Zenodo set. Part 10 is January–December 2021 (doi 10.7802/2472), part 11 is January–August 2022 (doi 10.7802/2473), and part 12 is September 2022–June 2023. The GESIS record says non-commercial research, not CC BY. A third-party downloader describes about 30 monthly files of roughly 3–5 GB each. I did not measure those files. The Zenodo copy of part 10 is restricted.

The full files can thicken nodes that the 5 percent sample barely covers. They do not by themselves repair Tesla in parts 1–9: those parts were linked with Wikipedia dumps that returned `Tesla_Motors` and not `Tesla,_Inc.` Parts 10–12 use 2022 and 2023 dumps, so the Tesla title may appear there. That is a possibility, not a count.

TweetsCOV19 is a COVID-keyword subset of TweetsKB, October 2019 through August 2022, CC BY 4.0, with Wikipedia entities and SentiStrength, and no tweet text. Its SPARQL endpoint is the full subset, not a 5 percent sample. It is a pandemic corpus. It does not replace a general brand series. No hydration and no platform API.

## News text

NELA-GT-2022 has 1,778,361 articles from 361 outlets, 1 January through 31 December 2022, with dates and body text (doi 10.7910/DVN/AMCV2H). The authors replace tokens with `@` so the articles cannot be read as news, about 7 percent of a long article. There is no entity link and no document sentiment. The pages checked do not state an open license. A classifier can run on the damaged text, and a hand label would be labeling damaged sentences. CC-News stays rejected from Phase 1B. The guide's dataset is the text source to audit when it arrives.

## One GDELT scan

Read only `date`, `lang`, `score`, a hash of `url`, `entity.wikipediaUrl`, and `entity.mid`. Filter English and the study dates. Do not select article URLs. One 28-day slice of that shape is 3.33 GB, so the full span is about 426 GB. Name filters do not reduce the scan. Putting every current and proposed brand in the same query does not add a second scan. Dry-run the first slice, record the job, and stop at 10 GB per slice or at the monthly cap.

`sgnn-csp` should not run that scan before 1 November 2026. After the reset, the 426 GB fit in one month on this project, with room left. No friend's account is required if the scan waits until November. One extra project is required only if the scan has to happen before the reset. Three projects would be required only for the 2.1 TB wide unnest, which this design does not use. Each login is `gcloud auth login`, done by you. Usage is appended to `eval/results/bq_ledger.jsonl` with the project id.

## Adapter

`configs/source_adapter.json` is the row every source must produce: node, source, arm, date, document id, score, and the list of study nodes in that document. The daily reduction is document count, scored count, and score sum. When the guide's news file arrives, it gets the same audit as the others: license, dates, text, entity tags, coverage, and a per-source planning SD logged before any outcome. It joins Arm B news, or it becomes its own arm. That choice is logged before any outcome. Arms stay unpooled.
