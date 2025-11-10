# 10K Insight Agent — End‑User UI Guide

This guide is for non‑technical users. It explains how to navigate the web app, run analyses, and read results. No installs or code required.

---

## Access

- Open the web app URL shared by your team. Typical local URL: http://localhost:3000
- Works in any modern browser (Chrome, Edge, Safari, Firefox).

---

## What You Can Do

- Queue analysis for one or many companies
- Filter and preview companies from the SEC
- Track live progress of running jobs
- Review pain points with citations and confidence
- See product matches with fit scores and evidence
- View ready‑to‑use pitches per persona
- Monitor overall metrics (time and token usage)

---

## Layout Overview

- Sidebar navigation (left): main sections of the app
- Top area: page title and, on some screens, filters/actions
- Content area: tables, cards, and charts for the selected section

Main sections
- Dashboard: high‑level metrics and quick links
- Analysis Queue: start analyses and monitor active jobs
- Company Insights: deep‑dive into a specific company’s results
- Top Pitches: best product‑to‑company matches across all results
- Metrics: processing time, token usage, cache hits

---

## Common Tasks (Step‑by‑Step)

1) Analyze specific companies (fastest)
1. Go to Analysis Queue → Company List
2. Paste company names, one per line (e.g., Microsoft, Apple, Tesla)
3. Optional: check “Force re‑analyze” to skip the cache and refresh results
4. Click Start Analysis
5. Switch to Active Jobs (on the same page) to watch progress

2) Analyze by filters (discover new companies)
1. Go to Analysis Queue → Filter Search
2. Choose filters such as Market Cap (SMALL/MID/LARGE/MEGA), Industry, and Sector
3. Click Preview Companies from SEC to review the list
4. Click Analyze X Companies to start
5. Track progress in Active Jobs

3) Track running jobs
- Statuses you may see: Queued, In Progress, Completed, Skipped, Failed
- You’ll also see an ETA; larger filings take longer
- Refresh happens automatically every few seconds

4) Review a company’s results
1. Go to Company Insights
2. Search for or select a company
3. Review sections:
   - Pain Points: themes, rationale, confidence, and direct quotes
   - Product Matches: products, fit scores, and evidence
   - Pitches: persona‑aware email/notes you can use immediately
   - Citations: references into the 10‑K (e.g., Item 1A, page numbers)

5) Explore best opportunities
1. Go to Top Pitches
2. Sort or filter by score, product, or company
3. Click through to open the underlying company details

6) Check system metrics
1. Go to Metrics
2. Review token usage, processing time, and cache hit rates
3. Use this to estimate cost/speed and plan batch sizes

Tips
- Use “Force re‑analyze” when you want fresh results after changing your product catalog
- Batch multiple companies together to save time
- Start with MEGA/LARGE caps for faster demos; SMALL/MID can reveal more varied pains

---

## Interpreting Results

- Pain Points
  - Each theme includes a rationale (why it matters) and confidence score
  - Quotes provide exact supporting text from the 10‑K
- Product Matches
  - Fit Score (0–100) reflects how well a product addresses a pain point
  - “Why it fits” and “Evidence” summarize the linkage
- Pitches
  - Persona‑aware messages you can adapt for outreach
  - Use the highest‑scoring matches to prioritize outreach

---

## Autonomous Mode (If Enabled by Your Team)

- Your workspace may auto‑analyze companies on a schedule
- You’ll see new results appear in Company Insights and Top Pitches
- You don’t need to start runs manually unless you want ad‑hoc analysis

---

## Quick Answers

- How long does it take? Typically 2–3 minutes per company
- Can I refresh results? Yes, check “Force re‑analyze” before starting
- Do I need an account? Your admin will share access; no extra setup needed
- Where are citations? In Company Insights, alongside each pain point/match

---

## Getting Help

- If something looks stuck, refresh the page after a minute
- For persistent issues, contact your admin with the time of the issue and the company name(s)

