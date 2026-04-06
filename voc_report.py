#!/usr/bin/env python3
"""
VOC Analysis Report Generator — Compare phone answer complaints across industries.
Usage: python3 voc_report.py <csv1> <csv2> <csv3> ... -o <output.md>
"""
import csv
import re
import sys
from collections import Counter
from pathlib import Path


def load_reviews(csv_path):
    reviews = []
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            reviews.append(row)
    return reviews


def analyze_industry(reviews):
    """Analyze reviews for one industry."""
    if not reviews:
        return {}

    total = len(reviews)
    businesses = set(r.get("business_name", "") for r in reviews)

    # Keyword frequency
    keyword_counts = Counter(r.get("matched_keyword", "").lower() for r in reviews)

    # Rating distribution
    ratings = Counter()
    for r in reviews:
        rating_text = r.get("review_rating", "")
        match = re.search(r"(\d)", rating_text)
        if match:
            ratings[int(match.group(1))] += 1

    # Top offending businesses
    biz_counts = Counter(r.get("business_name", "") for r in reviews)

    # Common complaint themes
    themes = {
        "voicemail": 0,
        "no_callback": 0,
        "unresponsive": 0,
        "poor_communication": 0,
        "ignored": 0,
    }
    for r in reviews:
        text = (r.get("review_text", "") + " " + r.get("matched_keyword", "")).lower()
        if any(w in text for w in ["voicemail", "voice mail"]):
            themes["voicemail"] += 1
        if any(w in text for w in ["call back", "callback", "return call", "got back", "gets back"]):
            themes["no_callback"] += 1
        if any(w in text for w in ["unresponsive", "not responsive", "no response", "never respond"]):
            themes["unresponsive"] += 1
        if any(w in text for w in ["communication", "communicate"]):
            themes["poor_communication"] += 1
        if any(w in text for w in ["ignored", "ignoring", "ignore"]):
            themes["ignored"] += 1

    return {
        "total_complaints": total,
        "unique_businesses": len(businesses),
        "keyword_counts": keyword_counts.most_common(10),
        "rating_distribution": dict(sorted(ratings.items())),
        "top_offenders": biz_counts.most_common(10),
        "themes": themes,
        "avg_rating": sum(k * v for k, v in ratings.items()) / max(sum(ratings.values()), 1),
        "sample_reviews": [r.get("review_text", "")[:200] for r in reviews[:5]],
    }


def generate_report(data_by_industry, output_path):
    """Generate markdown VOC comparison report."""
    lines = []
    lines.append("# VOC Analysis Report: Phone Responsiveness Complaints")
    lines.append("")
    lines.append("**Analysis Focus:** Reviews mentioning unanswered phone calls, no callbacks, voicemail issues")
    lines.append(f"**Industries Compared:** {', '.join(data_by_industry.keys())}")
    lines.append(f"**Region:** Texas")
    lines.append("")

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("| Industry | Total Complaints | Businesses Affected | Avg Rating | Top Issue |")
    lines.append("|----------|-----------------|--------------------:|------------|-----------|")
    for industry, stats in data_by_industry.items():
        top_theme = max(stats["themes"].items(), key=lambda x: x[1])[0] if stats["themes"] else "N/A"
        top_theme_label = top_theme.replace("_", " ").title()
        lines.append(
            f"| {industry} | {stats['total_complaints']} | "
            f"{stats['unique_businesses']} | "
            f"{stats['avg_rating']:.1f} | {top_theme_label} |"
        )
    lines.append("")

    # Solvea Opportunity Score
    lines.append("## Solvea.cx Opportunity Assessment")
    lines.append("")
    for industry, stats in data_by_industry.items():
        tc = stats["total_complaints"]
        ub = stats["unique_businesses"]
        # Higher complaints per business = bigger pain point = bigger opportunity
        intensity = tc / max(ub, 1)
        if intensity > 3:
            score = "HIGH"
            emoji = "🔴"
        elif intensity > 1.5:
            score = "MEDIUM"
            emoji = "🟡"
        else:
            score = "LOW"
            emoji = "🟢"
        lines.append(f"### {industry}: {emoji} {score} Opportunity")
        lines.append(f"- **{tc} complaints** across **{ub} businesses** ({intensity:.1f} complaints/business)")
        lines.append(f"- Average rating of complainers: **{stats['avg_rating']:.1f}/5**")
        lines.append(f"- **Pitch angle:** \"Your Yelp reviews show customers can't reach you by phone. "
                     f"Solvea answers every call 24/7 for free — no missed customers, no bad reviews.\"")
        lines.append("")

    # Detailed Industry Breakdown
    for industry, stats in data_by_industry.items():
        lines.append(f"## {industry} — Detailed Analysis")
        lines.append("")

        # Complaint Themes
        lines.append("### Complaint Themes")
        lines.append("")
        lines.append("| Theme | Count | % of Total |")
        lines.append("|-------|------:|----------:|")
        for theme, count in sorted(stats["themes"].items(), key=lambda x: -x[1]):
            pct = count / max(stats["total_complaints"], 1) * 100
            lines.append(f"| {theme.replace('_', ' ').title()} | {count} | {pct:.0f}% |")
        lines.append("")

        # Top Keywords
        lines.append("### Top Keywords")
        lines.append("")
        for kw, count in stats["keyword_counts"][:8]:
            lines.append(f"- \"{kw}\" — {count} mentions")
        lines.append("")

        # Top Offenders
        lines.append("### Businesses with Most Complaints")
        lines.append("")
        lines.append("| Business | Complaints |")
        lines.append("|----------|----------:|")
        for biz, count in stats["top_offenders"][:10]:
            lines.append(f"| {biz} | {count} |")
        lines.append("")

        # Rating Distribution
        lines.append("### Rating Distribution of Complainers")
        lines.append("")
        for star in range(1, 6):
            count = stats["rating_distribution"].get(star, 0)
            bar = "█" * count
            lines.append(f"  {star}★ | {bar} {count}")
        lines.append("")

        # Sample Reviews
        lines.append("### Sample Reviews")
        lines.append("")
        for i, sample in enumerate(stats["sample_reviews"][:3], 1):
            lines.append(f"> {i}. \"{sample}...\"")
            lines.append("")

    # Cross-Industry Insights
    lines.append("## Cross-Industry Insights")
    lines.append("")

    industries = list(data_by_industry.keys())
    if len(industries) >= 2:
        sorted_by_intensity = sorted(
            data_by_industry.items(),
            key=lambda x: x[1]["total_complaints"] / max(x[1]["unique_businesses"], 1),
            reverse=True,
        )
        lines.append(f"1. **Highest complaint intensity:** {sorted_by_intensity[0][0]} — "
                     f"these businesses lose the most customers to missed calls")
        lines.append(f"2. **Most affected businesses:** "
                     f"{max(data_by_industry.items(), key=lambda x: x[1]['unique_businesses'])[0]}")

        # Common pattern
        all_themes = Counter()
        for stats in data_by_industry.values():
            for theme, count in stats["themes"].items():
                all_themes[theme] += count
        top_universal = all_themes.most_common(1)[0] if all_themes else ("N/A", 0)
        lines.append(f"3. **Universal #1 complaint:** {top_universal[0].replace('_', ' ').title()} "
                     f"({top_universal[1]} total mentions across all industries)")
    lines.append("")

    # Solvea Outreach Recommendations
    lines.append("## Solvea Outreach Recommendations")
    lines.append("")
    lines.append("### Priority Targets")
    lines.append("")
    lines.append("Businesses with 2+ phone complaints are prime Solvea prospects:")
    lines.append("")
    all_offenders = []
    for industry, stats in data_by_industry.items():
        for biz, count in stats["top_offenders"]:
            if count >= 2:
                all_offenders.append((industry, biz, count))
    all_offenders.sort(key=lambda x: -x[2])
    for industry, biz, count in all_offenders[:20]:
        lines.append(f"- **{biz}** ({industry}) — {count} phone complaints")
    lines.append("")

    lines.append("### Outreach Script")
    lines.append("")
    lines.append("> Hi [Name], I noticed your [Industry] business has some Yelp reviews mentioning ")
    lines.append("> difficulty reaching you by phone. Solvea is a free AI receptionist that answers ")
    lines.append("> calls 24/7, books appointments, and responds across phone, text, and chat — ")
    lines.append("> so you never miss a customer. Takes 3 minutes to set up, no credit card needed. ")
    lines.append("> Would you like to try it?")
    lines.append("")

    report = "\n".join(lines)
    Path(output_path).write_text(report, encoding="utf-8")
    print(f"Report saved to: {output_path}")
    return report


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 voc_report.py <csv1> [csv2] [csv3] -o <output.md>")
        print("Example: python3 voc_report.py lawyers.csv locksmith.csv autorepair.csv -o report.md")
        sys.exit(1)

    csv_files = []
    output_path = None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "-o" and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]
            i += 2
        else:
            csv_files.append(sys.argv[i])
            i += 1

    if not output_path:
        output_path = "/Users/guozhen/Desktop/voc_report.md"

    data_by_industry = {}
    for csv_file in csv_files:
        reviews = load_reviews(csv_file)
        if reviews:
            industry = reviews[0].get("industry", Path(csv_file).stem)
            data_by_industry[industry] = analyze_industry(reviews)
            print(f"Loaded {len(reviews)} reviews for {industry}")
        else:
            print(f"Warning: No reviews in {csv_file}")

    if data_by_industry:
        generate_report(data_by_industry, output_path)
    else:
        print("No data to analyze!")


if __name__ == "__main__":
    main()
