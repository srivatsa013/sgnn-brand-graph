# Phase 1B: brand-reputation data audit

Date: 2026-10-12. Phase 2 is paused. No knowledge graph was built in this pass. No H1–H4 outcome was computed. No candidate below was downloaded. FNSPID and StockTwits were not deleted.

The locked domain is brand reputation. This audit asks whether a public, dated, pre-built source measures that domain more directly than FNSPID stock news and StockTwits investor posts. It does not change the project. Coverage and power were not re-estimated, because no replacement corpus was small enough to use without a download this pass was not authorized to make. The Phase 1 gates stand.

## Recommendation

The rejections below of Yelp, Reddit, CC-News, RepLab, the small Kaggle set, and Amazon reviews as an event source stand. Phase 1C was accepted on 2026-10-13 with two arms, not with a source replacement. Arm A remains FNSPID and StockTwits for all four ecosystems. Arm B adds TweetsKB for Apple, Microsoft, and Alphabet, and GDELT only if that probe passes. The rules are in `DECISIONS_LOG.md` and `reports/pre_registration.md` section 13.

## What was checked

| Source | Closer to brand reputation than finance? | Usable here? | Why |
| --- | --- | --- | --- |
| FNSPID | No. Stock news. | Yes. Already extracted. | Fallback news source. Sentiment is not in the file. |
| StockTwits | No. Investor bullish/bearish labels. | Yes. Already extracted. | Fallback social source. |
| TweetsKB | Closer. Public Twitter, not a stock forum. | No. | No tweet text. Hydrating ids would be API collection. |
| GDELT GKG | Closer. General news. | Not without approval. | No article text. Tone is document-level. Full files are far above 50 GB. BigQuery was not used. |
| Amazon Reviews 2023 | Closer for products. Consumer stars and review text. | No, as an event source. | One product per review. CEOs are absent. Electronics alone is about 9.7 GB compressed. Not downloaded. |
| Yelp Open Dataset | Local-business reviews, not these firms. | No. | Eleven metro areas. Publication needs Yelp's approval. |
| Reddit dumps | Public discussion, if the terms allowed it. | No. | Academic Torrents states that no license is specified. Reddit's Data API terms require a separate agreement for research beyond the stated limits. |
| CC-News | General news text. | No. | No sentiment and no entity lists. Publisher rights remain. The archive is far above 50 GB. |
| RepLab 2013 | Yes. Reputation polarity on Twitter. | No. | Automotive, banking, universities, and music, June–December 2012. Tweet text is not included. |
| Kaggle brand-sentiment tweets | Named as brand sentiment. | No. | 8,589 training rows. Too small for the pre-registered event rule. The file was not opened. |

## TweetsKB

Opened: https://data.gesis.org/tweetskb/ on 2026-10-12. The annotation pipeline is also described in Dimitrov et al., TweetsCOV19, arXiv:2006.14492, which was opened.

Nearly 3.1 billion English, spam-filtered tweets, February 2013 through June 2023, when the Twitter API was closed. The same paper says the crawl is 1 percent of tweets and has run since January 2013. The pages opened do not state a timezone for the post date. Parts are monthly N3 files. Parts 1–9 are on Zenodo. Parts 10–12 are on GESIS. The homepage says the files are under Creative Commons Attribution 4.0. A direct Zenodo API read returned HTTP 504, so the Zenodo license field was not re-read. A byte size was not obtained. At this tweet count the corpus is not a laptop extract.

Fields present: tweet id, post date, encrypted user id, hashtags, user mentions, URLs, entities linked by Yahoo FEL to a Wikipedia dump, and a confidence score. Sentiment is SentiStrength on the tweet: a positive score from +1 to +5 and a negative score from −1 to −5. That is one pair of scores for the tweet, not a separate score for each entity. The homepage says the tweet text is not provided. Ids can be used to retrieve text. This audit does not do that, because retrieving tweets is API collection.

Per-tweet entity lists exist, so a co-mention exclusion could use linked entities. Alias counts for a product or CEO that FEL did not link require the text, which is absent. The published top-entity table, confidence threshold −1, as of December 2020, includes YouTube (11,031,812), Facebook (5,064,670), and Google (1,207,049). Apple, Microsoft, Tesla, iPhone, and the CEO names are not in that top-20 list. That is not a coverage count. No per-node day counts and no event or power numbers were computed.

A public SPARQL endpoint holds a 5 percent sample. It was not queried for these nodes.

## GDELT GKG

Codebook opened: GKG 2.1, 19 February 2015, https://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf. One file was checked with a header request only: `20261011120000.gkg.csv.zip` is 2,654,604 bytes, last modified 11 October 2026. The full archive was not downloaded. The GDELT data page, as returned in search on this date, says the 2015 GKG alone is over 2.5 TB. BigQuery was not used. A Google Cloud account would be required. Ask before any query.

Each row is one document. `V2.1DATE` is `YYYYMMDDHHMMSS` and is the document's publication date, not a shifted event date. The codebook does not say the clock is UTC. `V1ORGANIZATIONS` and `V2ENHANCEDORGANIZATIONS` list company and organization names, the latter with character offsets. `V1PERSONS` and `V2ENHANCEDPERSONS` do the same for people. There is no product field. A product name appears only if the organization or name engine tags it. The codebook says the organization engine errs toward inclusion and that names seen once or twice should be histogrammed and dropped. `V1.5TONE` is the tone of the whole document, from −100 to +100, with common values between −10 and +10. It is not a score for one named entity. Using it for an entity shift would assign the article's tone to every tagged name in that article.

`V2DOCUMENTIDENTIFIER` is a URL when the source collection is the open web. The article text is not in the file. Fetching those URLs would be scraping and was not done. Co-mention exclusion could use the tagged name lists. Alias counts for untagged product strings could not.

No per-node coverage and no power estimate.

## Amazon Reviews 2023

Opened: https://amazon-reviews-2023.github.io/ and the Hugging Face dataset card for `McAuley-Lab/Amazon-Reviews-2023`. Reviews run from May 1996 to September 2023. The documented review fields include `rating` (1.0 to 5.0), `title`, `text`, `asin`, `parent_asin`, `user_id`, and `timestamp` as unix time. Unix time is UTC. Item metadata has `store` and a `details` dictionary that can contain a brand, as in the worked example. Brand is not a required column of its own.

The Hugging Face card's Electronics split lists 43,886,944 reviews, a download size of 9,661,010,652 bytes, and an uncompressed size of 16,707,860,887 bytes. Electronics metadata is about 1.96 GB compressed. The card's total file size for the whole dataset is 750 GB. None of it was downloaded. Free disk was about 18 GB, so the Electronics slice alone would consume most of it.

License, from the Hugging Face discussion opened on the card: on 8 March 2024 the maintainers wrote that they are not in a position to assign a license and that the dataset is available primarily for research, subject to ethical guidelines and applicable law. On 8 December 2024 they replied that they saw no issue with use in a bachelor's thesis. That is not a standard open license.

A review is one shopper's rating of one product. Stars are a given score. Text is available, so a review that names another brand could be dropped. The design still does not fit. There is no series for a CEO. A competitor appears only if that competitor has its own reviewed products. Pooling iPhone reviews into an "Apple event" would be a different design from the pre-registered brand event. No node-day counts and no power estimate.

## Other sources

Yelp Open Dataset, https://www.yelp.com/dataset/documentation/main, opened 2026-10-12: 6,990,280 reviews, 150,346 businesses, 11 metropolitan areas. The JSON download is 4.35 GB compressed and 8.65 GB uncompressed. The dataset agreement grants academic use and requires Yelp's review before public presentation or publication. The documented businesses are local. This does not cover the four ecosystems, their products, or their CEOs. Not downloaded.

Reddit. The Academic Torrents record for comments and submissions from June 2005 through December 2024 says no license is specified and the work may be protected by copyright. Reddit's Data API terms, opened at https://redditinc.com/policies/data-api-terms, say research beyond the rate limits needs a separate agreement. No dump was downloaded. One monthly comment file on that torrent page is tens of gigabytes. A full dump is far larger.

CC-News, https://data.commoncrawl.org/crawl-data/CC-NEWS/index.html: WARC files of news pages, crawl started in 2016, released daily. Common Crawl's terms of use, last updated 7 March 2024, grant a limited license and say crawled pages remain subject to the site owners' terms. Users must respect third-party copyrights. The files contain article text. They do not contain sentiment labels or entity lists. A third-party extraction, Infini-News, reports about 1.36 billion articles and about 1.7 TB compressed. That corpus was not opened as a file and was not downloaded. Raw CC-News was not sized beyond that public description. It is above the 50 GB line.

RepLab 2013, https://nlp.uned.es/replab2013/: more than 142,000 English and Spanish tweets, 61 entities, domains automotive, banking, universities, and music/artists. Crawled 1 June 2012 through 31 December 2012. Reputation polarity is an annotated field. Tweet text is not included, because of Twitter's terms. A paper opened for the entity description uses BMW as the example. These four ecosystems are not the corpus. The Research Data Australia record displays both "all rights reserved" and CC BY-NC 3.0 AU. Those two lines were not reconciled. The 76 MB annotation bundle was not downloaded.

A Kaggle set titled "Brand Sentiment Analysis Dataset (Twitter)" has 8,589 training rows and 504 test rows. It was not opened. At that size it cannot supply the pre-registered daily event series for four ecosystems.

## Earlier idea

1. Wikidata competitor edges at −1. A SPARQL query on 2026-10-12 for English property labels containing "competitor", "competes", or "rival" returned one property, P7339, "Rivals.com ID", which is a sports-prospect identifier. A second query counted statements whose English label is exactly "competitor" on Apple (Q312), Microsoft (Q2283), Google (Q95), Alphabet (Q20800404), Tesla (Q478214), Meta Platforms (Q380), and Amazon (Q3884). The count is 0. A broader label search for "compet" returned sports-competition identifiers, not a firm-competitor relation. The earlier property search had already rejected P710, "participant". Competitor edges stay the study list, checked by hand, with provenance. That was already the plan.

2. SEC Exhibit 21 as a cross-check only. Latest 10-K exhibits opened:

- Apple Inc., Exhibit 21.1, period ended 27 September 2025, filed 31 October 2025. Regional Apple companies and Braeburn Capital. No iPhone, MacBook, or CEO.
- Microsoft Corporation, Exhibit 21, period ended 30 June 2026, filed 29 July 2026. Includes LinkedIn and Activision Blizzard. No Windows, Azure, or CEO.
- Alphabet Inc., Exhibit 21.01, period ended 31 December 2025, filed 5 February 2026. Google LLC, XXVI Holdings Inc., and Alphabet Capital US LLC. No YouTube, Android, or CEO. Google LLC is the operating company already treated as the same node as Alphabet. It is not an edge to a product node.
- Tesla, Inc., Exhibit 21.1, period ended 31 December 2025, filed 29 January 2026. Sales, service, insurance, and solar entities. No Model 3, Model S, or CEO.

Each filing says subsidiaries that are not significant in aggregate are omitted, so a missing name is not proof that the entity does not exist. Of the planned brand, product, and CEO edges, Exhibit 21 confirms 0. Toyota Motor Corp. and NIO Inc. file Form 20-F, not Form 10-K. Their recent annual reports on EDGAR are 20-F filings (Toyota 10 June 2026, NIO 10 April 2026). They do not file a 10-K Exhibit 21. Exhibit 21 does not replace Wikidata or DBpedia.

3. FinBERT. Not the primary scorer. Added to the Phase 3 plan in `reports/pre_registration.md` section 10 and `reports/gnn_task_spec.md` section 6: score the hand-labeled brand-domain sample with FinBERT and with the entity-aware classifier, and report both. The 0.70 macro-F1 gate is unchanged. FinBERT does not detect events.

4. Nine automotive firms and seven pharma firms. Not built. Logged as a parked extension. It would drop products and CEOs and add a second sector, which breaks the locked scope. Tesla's ecosystem already includes Ford, General Motors, Toyota, and NIO.

## What this pass did not do

No new corpus was downloaded. No BigQuery query was run. No tweet ids were hydrated. No article URLs were fetched. No event series, shift, or H1–H4 number was computed. The Phase 1 gates were not re-run, because the sources did not change.
