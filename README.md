# Sanctions News Monitor

[![Pages](https://github.com/SDCofA/sanctions-exposure-index/actions/workflows/pipeline.yml/badge.svg)](https://github.com/SDCofA/sanctions-exposure-index/actions/workflows/pipeline.yml)

Entity and network signals for sanctions exposure monitoring.

**Live dashboard:** https://sdcofa.github.io/sanctions-exposure-index/

## Published methodology

- **Source:** Google News RSS; query: `(sanctions OR OFAC OR embargo)`. Google News chooses the matching sources; this is a convenience sample, not a complete census.
- **Collection:** the scheduled pipeline fetches up to 50 linked headlines every six hours. The dashboard shows the first 15 and counts distinct publisher labels. If fetching fails, a previously fetched sample may be shown for at most 24 hours and is marked retained. Otherwise the feed is unavailable.
- **Output:** article count, publisher-label count, publication dates, and links. No severity, sentiment, probability, exposure, or geographic location is inferred. There is no predictive model.
- **Limit:** News coverage is not an official sanctions-list check, entity match, ownership graph, or exposure score. Search ranking, publisher coverage, duplication and publication delays bias the sample. Follow linked primary sources before drawing conclusions.

## Run locally

```bash
python -m pip install -r requirements.txt
python pipeline/sanctions_exposure_index_pipeline.py
python -m http.server 8000
```

Open `http://localhost:8000`. Direct `file://` access cannot fetch `data/output.json` in modern browsers.

## Automation

GitHub Actions refreshes public data every six hours and deploys the static dashboard to GitHub Pages. The published page uses a deterministic methodology note; it does not generate an AI interpretation of headlines.

## Data notice

Source availability varies. The dashboard identifies its generation time and operating mode in `data/output.json`. Article counts describe this RSS sample only; they are not risk indicators or verified ground truth.

## Brand

Published by SDCofA, the endorsed analytical unit of Monarch Castle Technologies. See [BRAND.md](BRAND.md) for approved asset use.
