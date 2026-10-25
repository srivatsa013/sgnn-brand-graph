# Positive-edge funnel and allow-list

Date: 2026-10-14. Pair counts only. No shift, no H1–H4 estimate, and no widened caliper. Phase 3 does not start.

## 1. H2 rule, locked before the counts

An H2 edge class, positive or competitor, is tested on an arm and a source only when that class has at least 10 matched pairs. The pre-registered calipers stay as they are: baseline-mean absolute difference at most 0.20, baseline SD ratio from 0.5 to 2, log mention absolute difference at most 0.693147, and log popularity absolute difference at most 1.098612. A class below 10 is not reported as underpowered, is not dropped, and is not rescued by a wider caliper. The fix has to keep the rules: more brands, dated ownership edges for subsidiaries or products, a larger or better control pool, or more data from a source already approved. Arms stay separate.

The locked unit is the arm and the source, pooled across ecosystems. On Arm A, after the LinkedIn cells below, news positive is 10, social positive is 31, news competitor is 27, and social competitor is 178. Each of those four is at or above 10. The news positive 10 are still all Tesla. The six ecosystem slices for Apple, Microsoft, and Alphabet are the ones below 10, and the fixes below are for those slices.

## 2. Positive-edge funnel

The class is the product and subsidiary edges, plus the CEO edges, because those CEO nodes are listed as positive nodes. Android is a positive node and has no ownership edge, so it is outside the class. Targets: Apple is iPhone, MacBook, and Apple CEO; Microsoft is LinkedIn, Windows, Azure, and Microsoft CEO; Alphabet is YouTube and Alphabet CEO.

A row is the number of brand events still in the class after that step. The window step uses the full series. The exclusion step drops documents that mention the event brand. The last step is a control inside the pre-registered calipers that also has both windows.

| Ecosystem | Source | Events | Both windows | After co-mention | Control in the calipers | Step that removes the most |
| --- | --- | --- | --- | --- | --- | --- |
| Apple | News | 14 | 14 | 0 | 0 | Co-mention, 14 |
| Apple | Social | 171 | 96 | 35 | 0 | Window requirement, 75 |
| Microsoft | News | 5 | 5 | 1 | 0 | Co-mention, 4 |
| Microsoft | Social | 110 | 29 | 16 | 2 | Window requirement, 81 |
| Alphabet | News | 15 | 15 | 5 | 0 | Co-mention, 10 |
| Alphabet | Social | 142 | 93 | 93 | 0 | Caliper, 93 |

Co-mention removes the news rows because the product and the CEO are named in articles that also name the brand. On Apple news, iPhone has both windows on all 14 events before the drop and on none after it. Azure does the same on all 5 Microsoft news events. Alphabet news keeps 5 YouTube events.

The window requirement removes the most social events for Apple and Microsoft because the target series is thin around the brand event. Windows has both windows on 0 of 110 Microsoft social events, before any drop. MacBook has both windows on 25 of 171 Apple social events before the drop and on 0 after it.

Alphabet social loses nothing at co-mention. YouTube keeps both windows on all 93 events. The caliper then removes all 93. Across 426 comparisons with a control that itself has a 14-day baseline, the passes are mean 189, SD 273, mention 96, and popularity 0. YouTube has 245 sitelinks. The popularity caliper needs a control with at least 82 sitelinks. The largest eligible communication control is CMCSA at 53. Twenty-three of the 93 events already pass mean, SD, and mention against a control that also has both windows, and fail only popularity. Sixty-four pass mean and SD against such a control. Two events have no target baseline. One has no control with a baseline.

Apple social's last 35 events are iPhone. iPhone has 128 sitelinks. The highest eligible information-technology control has 42. That misses the popularity caliper, so every iPhone comparison fails it.

### Candidate fixes, not applied

These keep the calipers. A number here is an upper bound from events already on disk, not a new pair count.

| Slice, now below 10 | Fix that keeps the rules | Upper bound on the events already counted |
| --- | --- | --- |
| Alphabet social, 0 | Product-level controls with at least 82 sitelinks and a mention volume near YouTube | 23 pairs if the new control matches the controls that already pass mention. 64 if it also matches YouTube's mention volume and still passes mean and SD |
| Apple social, 0 | A control with at least 43 sitelinks, in the same sector | At most the 35 iPhone events that reach the caliper. The other three calipers were not passed by any current control, so the pair gain is unmeasured |
| Apple news, 0; Microsoft news, 0; Alphabet news, 0 | A dated product or subsidiary whose articles do not also name the brand | Events that would reach the control step: 14, 4, and 10. The events that already survive exclusion still find no control, so the pair gain from co-mention relief alone is unmeasured |
| Microsoft social, 2 | More dated nodes with LinkedIn's shape, or controls with about 1 to 11 sitelinks, which is LinkedIn's popularity band (3 sitelinks) | LinkedIn already produced the 2 pairs. At most 14 further events already have both windows and no control |
| All six slices | The twelve candidate brands, once they are ecosystems and have their own events | No pair number. They are not in the event file. Chipotle's 1,064 dense social days are coverage, not pairs |
| Arm B, uncounted | The full TweetsKB stream and the GDELT scan | No pair number until those series exist |

## 3. LinkedIn cells and the new positive counts

LinkedIn's Arm A cells are in `series.sqlite` for days on or after 2016-06-13. News is the headline alias, scored with VADER on the headline. Social is the `LNKD` cashtag or the LinkedIn alias, one message once. Cells that exclude Microsoft drop documents that mention Microsoft.

| Series | Days | Scored | Days with at least 14 scored documents |
| --- | --- | --- | --- |
| News, all documents | 1,599 | 4,572 | 14 |
| News, Microsoft mentions dropped | 372 | 615 | 0 |
| Social, all messages | 1,667 | 1,885 | 4 |
| Social, Microsoft mentions dropped | 1,432 | 1,277 | 1 |

LinkedIn Corporation Q127278673 has 3 sitelinks. That number is now in the popularity table.

Arm-level positive matched pairs, same calipers as before:

| Source | Before the cells | After the cells |
| --- | --- | --- |
| News | 10, all Tesla | 10 |
| Social | 29, all Tesla | 31 |

The two new pairs are LinkedIn on Microsoft social events. Microsoft news stays at 0. Apple and Alphabet stay at 0.

## 4. Twelve candidate brands

They are on the GDELT and TweetsKB allow-list in `configs/scan_allowlist.json`, `configs/arm_b_dbpedia_uris.json`, and `configs/gdelt_match_rule.json`. They are not study ecosystems. The scale-up still waits for the guide. The New York Times Company and Hershey stay on the list. Their coverage decision waits until the GDELT scan has been run. Arm A dense days remain 0 and 5 for the Times, and 5 and 6 for Hershey.

Wikidata has no property labeled competitor. The snapshot date is 2026-10-12. The claim check is the live API on 2026-10-14. No proposed edge is in the graph.

| Brand | Proposed peer | What Wikidata states | Added |
| --- | --- | --- | --- |
| Chipotle | Darden | No claim links the two items | No |
| T-Mobile US | Dish Network | No claim links the two items | No |
| Hershey | General Mills; Kellanova | No claim links either pair | No |
| Colgate-Palmolive | Clorox; Kimberly-Clark | No claim links either pair | No |
| Chevron | Marathon Petroleum; Valero | No claim links either pair | No |
| NextEra Energy | Duke Energy; Southern Company | No claim links either pair | No |
| Eli Lilly | Amgen; Vertex | No claim links either pair | No |
| Nike | None found | No item-link to another pool company | No |
| Lowe's | None found | Home Depot is not stated | No |
| New York Times Company | None found | No item-link to another pool company | No |
| Mastercard | None found | Visa is not stated | No |
| John Deere | None found | Caterpillar is not stated | No |

Home Depot, Visa, and Caterpillar are inside the current two-hop neighborhood. Home Depot and Visa each reach Apple through The Vanguard Group. Caterpillar reaches General Motors through Electro-Motive Diesel. Adding one of them as the competitor would put the new ecosystem's negative edge inside that neighborhood, so the ecosystems would not be separate. The control exclusion would widen by that competitor's own two-hop set. Home Depot would newly block Lowe's, which is the candidate itself. Visa would newly block Mastercard. Caterpillar would newly block no further control ticker. They are not added.

Dated ownership, year precision, so the window starts on 1 January of that year. Statements with no P580 are not added. Undated positive-property statements: Nike 9, Chipotle 1, Lowe's 1, T-Mobile US 6, New York Times Company 1, Hershey 2, Colgate-Palmolive 19, Mastercard 11, Chevron 10, NextEra 2, John Deere 18, Eli Lilly 10.

| Child | Parent | From | Arm A news days (dense) | Arm A social days (dense) | Graph edge |
| --- | --- | --- | --- | --- | --- |
| Hurley International | Nike | 2002 | 3 (0) | 1 (0) | No. On the allow-list |
| Converse | Nike | 2003 | 287 (0) | 56 (0) | No. On the allow-list. Alias is capitalised Converse |
| Umbro | Nike | 2007 | 50 (0) | 12 (0) | No. On the allow-list |
| Toothpaste, the class Q35855 | Colgate-Palmolive | 1873 | Not scanned | Not scanned | No. A generic class, and not on the allow-list |

A dense day has at least 14 scored documents. None of the three Nike children reaches 14 such days in either Arm A source.

## 5. TweetsKB parts 1–9

Zenodo parts 1–9 are 97 monthly files and 367,170,428,974 bytes, CC BY 4.0. One file was timed: `month_2013-10.n3.gz`, 3,028,700,401 bytes. Curl resumed it and, at about four minutes, showed an average of 42,048 bytes per second and about 20 hours for that file. At that rate the nine parts take about 101 days. The transfer of this one file is still going. The other 96 files were not started. Peak disk for the plan stays one file, under the 10 GB cap. The reducer is `scripts/phase2_tweetskb_stream.py`. It keeps per-entity per-day count, scored count, and score sum, and the study-node list on each matching tweet, then deletes the compressed file. It has not been run, because the file is still incomplete.

The placebo-date planning SD was not rerun and is not frozen. On the 5 percent sample, the earlier draw still stands: 60 placebo dates, and no sector control with a 14-day baseline.

Thin nodes on that sample: T-Mobile US has 990 days and 5,819 tweets; the New York Times Company has 16 days and 16 tweets. Hershey was not in that query. Full-file coverage of those names is not measured yet.

Parts 10–12 were not downloaded. Part 10, January–December 2021, doi 10.7802/2472: GESIS says free access without registration, and data can only be used for non-commercial research. Part 11, January–August 2022, doi 10.7802/2473: GESIS says free access without registration. Part 12, September 2022–June 2023, doi 10.7802/2781: the homepage prints that doi with a mistyped letter; the record says free access without registration, and non-commercial research. University research is non-commercial, so the stated use allows it. No registration is required for the access lines that were retrieved.

## 6. GDELT dry run

The scan keeps the date, language, document score, a hash of the URL, and the entity Wikipedia title or mid. English, from 2016-11-14. The SQL filter is the current study nodes plus the step-4 allow-list: 61 titles and 14 mids. The control pool is in the TweetsKB list and is not in this GDELT filter. The filter does not shrink the bytes billed. It shrinks the result.

Project `sgnn-csp`. Account `singarajusrivatsa@gmail.com`. First slice 2016-11-14 inclusive through 2016-12-12 exclusive. Dry run: 3,333,846,320 bytes. The job is in `eval/results/bq_ledger.jsonl` with that project id, executed false. The real scan was not run. A BigQuery dry run returns bytes processed and does not return the result size. The same column set, without this title filter, dry-ran at the same 3,333,846,320 bytes on an earlier 28-day slice.

There are 128 slices of 28 days from 2016-11-14 through 2026-08-15. At 3.33 GB each, the span is about 426 GB. That fits one fresh 1 TB month.

The dry run already done:

```bash
bq query --project_id=sgnn-csp --use_legacy_sql=false --dry_run --format=json \
  "$(cat eval/results/phase2_gdelt_allowlist_scan.sql)"
```

The script that wrote that SQL and the ledger row is `scripts/phase2_gdelt_allowlist_scan.py`. It dry-runs the first slice only.

A real slice, not run, would be the same query with `--dry_run` removed, after a dry run under 10 GB, with the job id recorded. The dates in the SQL change for each of the 128 slices. I will not start that loop until you name the project.

`sgnn-csp` stays unused for the real scan until 1 November 2026. One friend's project can hold all 128 slices, because 426 GB fits in one 1 TB month. Three projects are for the 2.1 TB wide unnest, which this scan does not use.

When you want a friend's project, the login is yours:

```bash
gcloud auth login
gcloud config set project FRIEND_PROJECT_ID
gcloud config get-value account
gcloud config get-value project
```

Tell me the project id and that the login is done. The slices on that project would be 1 through 128, 2016-11-14 through 2026-08-15, unless you split them. Each job goes into `eval/results/bq_ledger.jsonl` with the project id and the account. I will not run `gcloud auth login`.

## Standing items

NELA-GT stays rejected. The text is damaged, and the pages checked state no license. The guide's dataset will go through `configs/source_adapter.json` when it arrives. Which arm it joins is logged before any outcome.

Stopped here for approval.
