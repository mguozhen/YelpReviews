#!/usr/bin/env python3
"""
Generic Yelp review scraper — filter for "no phone answer" complaints.
Usage: python3 yelp_scrape_generic.py <industry> <location> <output_file>
Example: python3 yelp_scrape_generic.py "Locksmith" "Texas" /Users/guozhen/Desktop/yelp_locksmith_reviews.csv
"""
import json
import time
import urllib.request
import csv
import re
import sys

CDP = "http://localhost:3456"
KEYWORDS = [
    "no answer", "no one answer", "nobody answer", "didn't answer", "did not answer",
    "don't answer", "do not answer", "won't answer", "never answer", "can't reach",
    "couldn't reach", "could not reach", "unreachable", "no response", "never respond",
    "didn't respond", "did not respond", "don't respond", "never call back",
    "didn't call back", "did not call back", "don't call back", "no call back",
    "no callback", "never called back", "doesn't return call", "didn't return call",
    "did not return call", "don't return call", "never return call", "won't return call",
    "doesn't pick up", "didn't pick up", "don't pick up", "never pick up", "won't pick up",
    "not picking up", "doesn't return my call", "doesn't return phone",
    "phone goes to voicemail", "straight to voicemail", "always voicemail",
    "goes to voicemail", "sent to voicemail", "left voicemail", "left message",
    "left a message", "left multiple message", "left several message",
    "never got back", "never gets back", "didn't get back", "did not get back",
    "impossible to reach", "hard to reach", "difficult to reach",
    "ignored my call", "ignoring my call", "ignore call", "ignored call",
    "unresponsive", "not responsive", "lack of communication", "poor communication",
    "no communication", "zero communication",
]

KEYWORD_PATTERN = re.compile("|".join(re.escape(k) for k in KEYWORDS), re.IGNORECASE)


def cdp_request(path, data=None):
    url = f"{CDP}{path}"
    if data:
        req = urllib.request.Request(url, data=data.encode(), method="POST")
    else:
        req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req, timeout=20)
        return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def new_tab(url):
    r = cdp_request(f"/new?url={urllib.request.quote(url, safe='')}")
    return r.get("targetId", "")


def close_tab(tid):
    cdp_request(f"/close?target={tid}")


def evaluate(tid, js):
    r = cdp_request(f"/eval?target={tid}", js)
    return r.get("value", "")


def extract_reviews(tid):
    js = r'''(() => {
  const reviews = [];
  // Yelp uses comment__09f24__ class containers with span[lang] for review text
  const comments = document.querySelectorAll("[class*=comment__09f24]");
  comments.forEach(c => {
    const spans = c.querySelectorAll("span[lang]");
    let text = "";
    spans.forEach(s => text += s.textContent.trim() + " ");
    text = text.trim();
    if (text.length > 30) {
      let rating = "";
      let author = "";
      let walker = c;
      for (let i = 0; i < 10 && walker; i++) {
        walker = walker.parentElement;
        if (!walker) break;
        if (!rating) {
          const re = walker.querySelector("[aria-label*='star rating']");
          if (re) rating = re.getAttribute("aria-label");
        }
        if (!author) {
          const ae = walker.querySelector("a[href*='/user_details']");
          if (ae) author = ae.textContent.trim();
        }
        if (rating && author) break;
      }
      reviews.push({text: text.substring(0,500), rating: rating || "", author: author || ""});
    }
  });

  // Fallback: also try span[lang] directly if no comment containers found
  if (reviews.length === 0) {
    const spans = document.querySelectorAll("span[lang]");
    spans.forEach(s => {
      const text = s.textContent.trim();
      if (text.length > 50) {
        let parent = s.closest("li") || s.parentElement;
        let rating = "";
        let author = "";
        if (parent) {
          const re = parent.querySelector("[aria-label*='star']");
          if (re) rating = re.getAttribute("aria-label") || "";
          const ae = parent.querySelector("a[href*='/user_details']");
          if (ae) author = ae.textContent.trim();
        }
        reviews.push({text: text.substring(0,500), rating: rating || "", author: author || ""});
      }
    });
  }

  return JSON.stringify(reviews);
})()'''
    raw = evaluate(tid, js)
    try:
        return json.loads(raw)
    except:
        return []


def get_biz_info(tid):
    js = r'''(() => {
  const name = document.querySelector("h1") ? document.querySelector("h1").textContent.trim() : "";
  const phoneEl = document.querySelector("a[href^='tel:'], p[class*='phone']");
  const phone = phoneEl ? phoneEl.textContent.trim() : "";
  const addrEl = document.querySelector("address, [class*='address'], a[href*='maps']");
  const address = addrEl ? addrEl.textContent.trim().substring(0, 100) : "";
  const ratingEl = document.querySelector("[aria-label*='star rating']");
  const rating = ratingEl ? ratingEl.getAttribute("aria-label") : "";
  const reviewCountEl = document.querySelector("a[href='#reviews']");
  const reviewCount = reviewCountEl ? reviewCountEl.textContent.trim() : "";
  return JSON.stringify({name, phone, address, rating, reviewCount});
})()'''
    raw = evaluate(tid, js)
    try:
        return json.loads(raw)
    except:
        return {"name": "", "phone": "", "address": "", "rating": "", "reviewCount": ""}


def extract_slugs_from_search(tid):
    raw = evaluate(tid, r'''(() => {
      const all = [...document.querySelectorAll("a")].filter(a => {
        const h = a.getAttribute("href") || "";
        return h.startsWith("/biz/") && !h.includes("ad_business_id");
      });
      const seen = new Set();
      const results = [];
      all.forEach(a => {
        const slug = a.getAttribute("href").split("?")[0];
        const name = a.textContent.trim();
        if (!seen.has(slug) && name.length > 2 && name !== "more") {
          seen.add(slug);
          results.push(slug);
        }
      });
      return JSON.stringify(results);
    })()''')
    try:
        return json.loads(raw)
    except:
        return []


def collect_slugs(industry, location, max_pages=30):
    """Collect business slugs from multiple search pages."""
    all_slugs = []
    seen = set()

    for start in range(0, max_pages * 10, 10):
        loc_encoded = urllib.request.quote(location)
        ind_encoded = urllib.request.quote(industry)
        url = f"https://www.yelp.com/search?find_desc={ind_encoded}&find_loc={loc_encoded}&start={start}"
        tid = new_tab(url)
        if not tid:
            continue

        time.sleep(4)

        title = evaluate(tid, "document.title")
        if "verif" in title.lower():
            time.sleep(5)
            title = evaluate(tid, "document.title")

        slugs = extract_slugs_from_search(tid)
        close_tab(tid)

        new_count = 0
        for s in slugs:
            if s not in seen:
                seen.add(s)
                all_slugs.append(s)
                new_count += 1

        print(f"  Page {start//10 + 1}: {len(slugs)} found, {new_count} new (total: {len(all_slugs)})")

        if len(slugs) == 0 or new_count == 0:
            print("  No more results, stopping pagination.")
            break

        time.sleep(1)

    return all_slugs


def scrape_business(slug, results, industry, target_count=100):
    url = f"https://www.yelp.com{slug}"
    tid = new_tab(url)
    if not tid:
        print(f"  SKIP {slug}: failed to open tab")
        return False

    time.sleep(4)

    title = evaluate(tid, "document.title")
    if "verif" in title.lower():
        time.sleep(5)
        title = evaluate(tid, "document.title")
        if "verif" in title.lower():
            close_tab(tid)
            return False

    biz = get_biz_info(tid)
    biz_name = biz.get("name", slug)
    biz_phone = biz.get("phone", "")
    print(f"  {biz_name} | {biz_phone}")

    # Scroll to load reviews
    for scroll_y in [1500, 3000, 5000, 7000]:
        cdp_request(f"/scroll?target={tid}&y={scroll_y}")
        time.sleep(0.5)

    reviews = extract_reviews(tid)
    print(f"    Found {len(reviews)} reviews total")

    matched = 0
    for rev in reviews:
        text = rev.get("text", "")
        match = KEYWORD_PATTERN.search(text)
        if match:
            matched += 1
            results.append({
                "industry": industry,
                "business_name": biz_name,
                "business_phone": biz_phone,
                "business_address": biz.get("address", ""),
                "business_rating": biz.get("rating", ""),
                "business_review_count": biz.get("reviewCount", ""),
                "business_url": url,
                "review_author": rev.get("author", ""),
                "review_rating": rev.get("rating", ""),
                "matched_keyword": match.group(),
                "review_text": text[:500],
            })
            print(f"    ✓ MATCH [{match.group()}]: {text[:80]}...")

    print(f"    Matched: {matched}")
    close_tab(tid)

    return len(results) >= target_count


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 yelp_scrape_generic.py <industry> <location> <output_file> [target_count]")
        sys.exit(1)

    industry = sys.argv[1]
    location = sys.argv[2]
    output_file = sys.argv[3]
    target_count = int(sys.argv[4]) if len(sys.argv) > 4 else 100

    print(f"{'='*60}")
    print(f"YELP SCRAPER — {industry} in {location}")
    print(f"Target: {target_count} reviews mentioning phone/communication issues")
    print(f"Output: {output_file}")
    print(f"{'='*60}")

    # Step 1: Collect business slugs
    print(f"\nStep 1: Collecting {industry} businesses in {location}...")
    slugs = collect_slugs(industry, location, max_pages=30)
    print(f"Total businesses found: {len(slugs)}")

    # Step 2: Scrape reviews
    print(f"\nStep 2: Scraping reviews...")
    results = []
    for i, slug in enumerate(slugs):
        if len(results) >= target_count:
            break
        print(f"\n[{i+1}/{len(slugs)}] {slug} (found so far: {len(results)})")
        try:
            done = scrape_business(slug, results, industry, target_count)
            if done:
                break
        except Exception as e:
            print(f"  ERROR: {e}")
        time.sleep(1)

    # Save results
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "industry", "business_name", "business_phone", "business_address",
            "business_rating", "business_review_count", "business_url",
            "review_author", "review_rating", "matched_keyword", "review_text"
        ])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n{'='*60}")
    print(f"DONE! {industry}: Found {len(results)} matching reviews")
    print(f"Saved to: {output_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
