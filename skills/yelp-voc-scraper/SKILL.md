---
name: yelp-voc-scraper
description: "Scrape Yelp reviews by industry and location, filter by complaint keywords, generate VOC analysis reports. Triggers: yelp reviews, voc analysis, phone complaints, missed calls reviews"
allowed-tools: Bash, Read, Write, Edit
metadata:
  openclaw:
    homepage: https://github.com/mguozhen/YelpReviews
---

# Yelp VOC Scraper

Scrape Yelp reviews filtered by complaint keywords (missed calls, no answer, voicemail, etc.) and generate Voice of Customer analysis reports comparing industries.

## What It Does

1. Searches Yelp for businesses by industry + location
2. Visits each business page, extracts reviews matching phone/communication complaint keywords
3. Saves structured data (business name, phone, URL, review text, rating, matched keyword)
4. Generates a comparative VOC report with:
   - Cross-industry complaint comparison
   - Keyword frequency analysis
   - Top offender businesses
   - Rating distributions
   - Solvea.cx opportunity scoring
   - Ready-to-use outreach scripts

## Requirements

- Chrome with remote debugging enabled (`chrome://inspect/#remote-debugging`)
- CDP proxy running at localhost:3456 (web-access skill)
- Python 3.9+

## Usage

### Scrape reviews

```bash
# Edit yelp_scraper.py to set industry, location, and target count
python3 yelp_scraper.py
```

### Generate VOC report from existing data

```python
from voc_report import analyze_industry, generate_report
import json

data = {}
for industry, path in {"Lawyers": "data/lawyers.json", "Locksmith": "data/locksmith.json"}.items():
    reviews = json.load(open(path))
    data[industry] = analyze_industry(reviews)

report = generate_report(data, "voc_report.md")
```

## Keyword Filters

The scraper matches 40+ phone/communication complaint keywords:

> no answer, didn't answer, voicemail, never call back, unresponsive, poor communication, zero communication, lack of communication, didn't pick up, hard to reach, ignored, left message, straight to voicemail, no response, won't return, doesn't return, never returned, phone rang, hung up, disconnected, can't get through, couldn't reach, nobody answered, no one answered, didn't respond, won't respond, never responds, unreachable, ghosted

## Output Format

Each review is saved as:

```json
{
  "business_name": "Example Law Firm",
  "business_phone": "(555) 123-4567",
  "business_url": "https://yelp.com/biz/example-law-firm",
  "review_author": "John D.",
  "review_rating": "1 star rating",
  "matched_keyword": "no answer",
  "review_text": "Called three times, no answer..."
}
```
