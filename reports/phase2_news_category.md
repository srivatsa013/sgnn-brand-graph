# HuffPost news-category mention check

2026-10-17. Source: `heegyu/news-category-dataset`, CC BY 4.0, file `data/interim/news_category/data.json`. 209,527 articles, 2012-01-28 through 2022-09-23. The span is 3,892 calendar days and 3,890 of those days have at least one article. The text counted is the headline plus `short_description`. One article counts once per node. No sentiment score and no shift was computed.

Share of days is mention-days divided by those 3,892 calendar days. The 14-of-28 check asks whether any 28-day calendar window inside 2012-01-01 through 2017-12-31 contains 14 days with at least one mention. A mention-floor day has at least 5 articles for that node. That is the event rule’s mention minimum. It is not a detected event.

## Match rule

Logged aliases are used, with a word boundary. CEO names count only inside the windows in `configs/ceo_tenures.json`. Bare Windows, bare Snap, bare HP, bare GM, and bare Musk are not assigned.

| Node | What counts | What was left out |
| --- | --- | --- |
| Apple | Capital `Apple` | 59 articles whose hit was food, Fiona Apple, or the Big Apple |
| Windows | `Microsoft Windows`, `Windows 7`, `Windows 8`, `Windows 10`, `Windows 11` | 106 articles with bare `Windows` |
| SNAP | `Snapchat`, `Snap Inc` | 44 articles with bare `Snap` |
| HPQ | `Hewlett-Packard`, `Hewlett Packard`, `HP Inc` | 24 articles with bare `HP` |
| GM | `General Motors` | 29 articles with bare `GM` |
| AMZN | `Amazon` | 15 rainforest or river articles |
| Tesla | `Tesla` | Nikola Tesla and Tesla coil when the company is not also named |
| F | `Ford` | 72 articles naming another Ford or the Ford Foundation |
| Alphabet | `Google`, `Alphabet` | 21 articles about the letter alphabet. The verb “google” stays in |
| Azure | Capital `Azure`, including `Microsoft Azure` | 3 lowercase color uses (`azure lakes`, `azure ocean`) |
| Model S | Capital `Model S` and `ModelS` | The word `models` (394 articles) |
| Meta | `Facebook`, `Meta Platforms` | Bare `Meta` |
| Chipotle, Chevron | Capital form | Lowercase pepper and chevron-pattern uses |
| Colgate-Palmolive | `Colgate`, `Colgate-Palmolive` | 1 Colgate University article |
| John Deere, Eli Lilly, Lowe's | The full name | Bare Deere, Lilly, and Lowe |

Facebook and Pinterest counts include ordinary “on Facebook” and “on Pinterest” lines. Those are product mentions. They are not a separate corporate-news series.

## Totals

Five nodes pass the 14-of-28 baseline in 2012–2017: Apple, Alphabet, iPhone, Meta, and PINS. The other 40 do not. YouTube has 325 mention-days and still has no 28-day window in that period with 14 observed days.

In 2012–2017 there are 119 node-days with at least 5 mentions. 113 of those also have 14 observed days in the prior 28. The 119 are Meta 82 (81 with the baseline), Pinterest 34 (32 with the baseline), Apple 2 (neither with the baseline), and iPhone 1 (without the baseline). Over the full file the same figures are 121 and 114.

| Node | Mentions | Days ≥1 | Share | Days ≥3 | Days ≥5 | Busiest day | 14-of-28 |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Apple | 493 | 399 | 10.3% | 13 | 2 | 2015-09-09 (7) | yes |
| Microsoft | 87 | 80 | 2.1% | 1 | 0 | 2015-10-06 (3) | no |
| Alphabet | 530 | 452 | 11.6% | 10 | 0 | 2017-08-11 (3) | yes |
| Tesla | 76 | 71 | 1.8% | 0 | 0 | 2017-02-07 (2) | no |
| iPhone | 331 | 284 | 7.3% | 7 | 1 | 2016-03-21 (5) | yes |
| MacBook | 17 | 16 | 0.4% | 0 | 0 | 2012-07-15 (2) | no |
| Windows | 11 | 9 | 0.2% | 0 | 0 | 2015-10-06 (2) | no |
| Azure | 0 | 0 | 0.0% | 0 | 0 | — | no |
| LinkedIn | 34 | 34 | 0.9% | 0 | 0 | 2016-12-22 (1) | no |
| YouTube | 370 | 325 | 8.4% | 6 | 0 | 2018-04-04 (3) | no |
| Android | 40 | 37 | 1.0% | 0 | 0 | 2016-12-22 (2) | no |
| Model 3 | 2 | 2 | 0.1% | 0 | 0 | 2016-04-04 (1) | no |
| Model S | 7 | 7 | 0.2% | 0 | 0 | 2016-07-03 (1) | no |
| Apple CEO | 36 | 35 | 0.9% | 0 | 0 | 2014-10-31 (2) | no |
| Microsoft CEO | 3 | 3 | 0.1% | 0 | 0 | 2014-10-14 (1) | no |
| Alphabet CEO | 4 | 4 | 0.1% | 0 | 0 | 2016-06-09 (1) | no |
| Tesla CEO | 86 | 86 | 2.2% | 0 | 0 | 2022-07-20 (1) | no |
| DELL | 19 | 19 | 0.5% | 0 | 0 | 2017-09-02 (1) | no |
| HPQ | 11 | 10 | 0.3% | 0 | 0 | 2015-09-20 (2) | no |
| LOGI | 0 | 0 | 0.0% | 0 | 0 | — | no |
| Samsung | 65 | 61 | 1.6% | 0 | 0 | 2016-10-11 (2) | no |
| ORCL | 9 | 9 | 0.2% | 0 | 0 | 2017-12-14 (1) | no |
| CRM | 13 | 12 | 0.3% | 0 | 0 | 2015-11-05 (2) | no |
| IBM | 17 | 17 | 0.4% | 0 | 0 | 2017-06-23 (1) | no |
| ADBE | 9 | 9 | 0.2% | 0 | 0 | 2016-09-19 (1) | no |
| Meta | 2389 | 1211 | 31.1% | 298 | 84 | 2013-09-25 (8) | yes |
| AMZN | 361 | 331 | 8.5% | 2 | 0 | 2017-12-18 (3) | no |
| SNAP | 91 | 86 | 2.2% | 0 | 0 | 2018-03-15 (2) | no |
| PINS | 1180 | 576 | 14.8% | 156 | 34 | 2013-09-25 (7) | yes |
| F | 93 | 90 | 2.3% | 0 | 0 | 2018-10-03 (2) | no |
| GM | 10 | 10 | 0.3% | 0 | 0 | 2022-08-17 (1) | no |
| TM | 35 | 33 | 0.8% | 0 | 0 | 2012-08-22 (2) | no |
| NIO | 0 | 0 | 0.0% | 0 | 0 | — | no |
| Nike | 63 | 61 | 1.6% | 0 | 0 | 2012-08-14 (2) | no |
| Chipotle | 81 | 78 | 2.0% | 0 | 0 | 2015-12-23 (2) | no |
| Lowe's | 7 | 7 | 0.2% | 0 | 0 | 2020-07-08 (1) | no |
| T-Mobile US | 12 | 12 | 0.3% | 0 | 0 | 2019-07-26 (1) | no |
| New York Times Co | 423 | 367 | 9.4% | 8 | 0 | 2017-07-20 (4) | no |
| Hershey | 14 | 14 | 0.4% | 0 | 0 | 2016-11-21 (1) | no |
| Colgate-Palmolive | 2 | 2 | 0.1% | 0 | 0 | 2016-02-08 (1) | no |
| Mastercard | 8 | 8 | 0.2% | 0 | 0 | 2022-09-10 (1) | no |
| Chevron | 16 | 16 | 0.4% | 0 | 0 | 2018-02-10 (1) | no |
| NextEra Energy | 0 | 0 | 0.0% | 0 | 0 | — | no |
| John Deere | 0 | 0 | 0.0% | 0 | 0 | — | no |
| Eli Lilly | 4 | 4 | 0.1% | 0 | 0 | 2016-11-01 (1) | no |

## Mentions by year

| Node | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Apple | 110 | 75 | 28 | 89 | 139 | 29 | 8 | 6 | 4 | 4 | 1 |
| Microsoft | 12 | 11 | 7 | 21 | 26 | 5 | 0 | 4 | 1 | 0 | 0 |
| Alphabet | 86 | 110 | 65 | 83 | 88 | 68 | 17 | 4 | 2 | 4 | 3 |
| Tesla | 0 | 2 | 9 | 16 | 30 | 9 | 5 | 1 | 0 | 4 | 0 |
| iPhone | 79 | 63 | 24 | 49 | 88 | 19 | 5 | 0 | 1 | 3 | 0 |
| MacBook | 9 | 3 | 0 | 2 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| Windows | 3 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| Azure | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| LinkedIn | 5 | 6 | 8 | 10 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| YouTube | 128 | 98 | 25 | 37 | 18 | 22 | 29 | 1 | 6 | 5 | 1 |
| Android | 8 | 6 | 1 | 9 | 11 | 0 | 3 | 1 | 1 | 0 | 0 |
| Model 3 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| Model S | 0 | 1 | 1 | 2 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| Apple CEO | 5 | 1 | 5 | 6 | 15 | 3 | 0 | 0 | 1 | 0 | 0 |
| Microsoft CEO | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Alphabet CEO | 1 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| Tesla CEO | 0 | 1 | 4 | 15 | 25 | 18 | 10 | 1 | 1 | 4 | 7 |
| DELL | 7 | 3 | 1 | 3 | 4 | 1 | 0 | 0 | 0 | 0 | 0 |
| HPQ | 0 | 0 | 0 | 6 | 3 | 0 | 0 | 0 | 1 | 1 | 0 |
| LOGI | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Samsung | 14 | 8 | 4 | 12 | 21 | 5 | 0 | 1 | 0 | 0 | 0 |
| ORCL | 2 | 1 | 1 | 1 | 3 | 1 | 0 | 0 | 0 | 0 | 0 |
| CRM | 0 | 0 | 2 | 5 | 3 | 0 | 1 | 1 | 0 | 1 | 0 |
| IBM | 2 | 2 | 2 | 8 | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| ADBE | 2 | 0 | 2 | 3 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| Meta | 593 | 913 | 257 | 156 | 187 | 131 | 106 | 18 | 11 | 10 | 7 |
| AMZN | 29 | 41 | 26 | 55 | 54 | 68 | 47 | 19 | 10 | 10 | 2 |
| SNAP | 0 | 8 | 6 | 14 | 42 | 14 | 7 | 0 | 0 | 0 | 0 |
| PINS | 446 | 619 | 97 | 7 | 8 | 3 | 0 | 0 | 0 | 0 | 0 |
| F | 6 | 16 | 16 | 9 | 14 | 10 | 17 | 4 | 0 | 0 | 1 |
| GM | 2 | 0 | 4 | 2 | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| TM | 17 | 2 | 4 | 6 | 3 | 1 | 2 | 0 | 0 | 0 | 0 |
| NIO | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Nike | 8 | 11 | 9 | 9 | 16 | 5 | 2 | 1 | 1 | 1 | 0 |
| Chipotle | 3 | 12 | 18 | 23 | 17 | 6 | 1 | 0 | 1 | 0 | 0 |
| Lowe's | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| T-Mobile US | 2 | 0 | 2 | 0 | 5 | 1 | 1 | 1 | 0 | 0 | 0 |
| New York Times Co | 42 | 54 | 42 | 61 | 68 | 88 | 48 | 5 | 8 | 3 | 4 |
| Hershey | 2 | 5 | 1 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| Colgate-Palmolive | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| Mastercard | 2 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 1 | 1 |
| Chevron | 4 | 2 | 3 | 5 | 0 | 1 | 1 | 0 | 0 | 0 | 0 |
| NextEra Energy | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| John Deere | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Eli Lilly | 2 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |

## Hand-label pool

Each node’s mention total above is the number of articles that name that node. An article that names two nodes is one item in each row and one item in the deduplicated pools.

- Articles naming Apple, Microsoft, Alphabet, or Tesla: **1,137**.
- Articles naming any tracked node in this check: **5,563**.

The 1,137 study-brand articles by category:

| Category | Articles |
| --- | ---: |
| TECH | 503 |
| BUSINESS | 148 |
| POLITICS | 59 |
| WELLNESS | 51 |
| FOOD & DRINK | 31 |
| ENTERTAINMENT | 31 |
| PARENTING | 26 |
| COMEDY | 25 |
| TRAVEL | 22 |
| STYLE & BEAUTY | 20 |
| BLACK VOICES | 19 |
| SCIENCE | 18 |
| WOMEN | 15 |
| HEALTHY LIVING | 13 |
| MEDIA | 11 |
| QUEER VOICES | 10 |
| TASTE | 10 |
| GREEN | 9 |
| WORLD NEWS | 8 |
| MONEY | 8 |
| U.S. NEWS | 7 |
| ARTS & CULTURE | 7 |
| IMPACT | 7 |
| WEDDINGS | 7 |
| HOME & LIVING | 6 |
| SPORTS | 6 |
| PARENTS | 6 |
| WEIRD NEWS | 6 |
| CRIME | 6 |
| ENVIRONMENT | 6 |
| DIVORCE | 6 |
| THE WORLDPOST | 4 |
| FIFTY | 4 |
| CULTURE & ARTS | 4 |
| RELIGION | 3 |
| GOOD NEWS | 3 |
| ARTS | 3 |
| LATINO VOICES | 2 |
| EDUCATION | 2 |
| COLLEGE | 2 |
| STYLE | 2 |
| WORLDPOST | 1 |

Counts are in `eval/results/phase2_news_category_counts.json`.
