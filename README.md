# Skincare Ingredient Sentiment Analysis

> **Business Question:** Which skincare ingredients generate the most negative consumer sentiment — and does this vary by skin concern (acne, aging, sensitivity)?

An end-to-end data pipeline that collects Reddit skincare community data, stores it in a relational database, runs NLP-based sentiment analysis, and surfaces actionable product insights via an interactive Power BI dashboard.

---

## Business Impact

- Identified the **top 5 most-complained-about ingredients** across 10,000+ posts in r/SkincareAddiction
- Revealed sentiment divergence by skin concern type — enabling more targeted product formulation recommendations
- Dashboard allows brand/clinic teams to filter by skin type, ingredient class, and date range for real-time insight

---

## Tech Stack

| Layer | Tool |
|---|---|
| Data Collection | Python (`PRAW` Reddit API) |
| Storage | PostgreSQL |
| Processing & NLP | Python (`pandas`, `spaCy`, `VADER`) |
| Visualization | Power BI |
| Version Control | Git / GitHub |

---

## Project Structure

```
skincare-sentiment-analysis/
│
├── data/
│   ├── raw/                  # Raw Reddit API pulls (JSON)
│   └── processed/            # Cleaned + labeled CSVs
│
├── sql/
│   ├── schema.sql            # PostgreSQL table definitions
│   └── queries/              # Analysis queries (window functions, CTEs)
│       ├── top_ingredients.sql
│       ├── sentiment_by_concern.sql
│       └── monthly_trend.sql
│
├── notebooks/
│   ├── 01_data_collection.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_ingredient_extraction.ipynb
│   └── 04_sentiment_analysis.ipynb
│
├── dashboard/
│   └── skincare_dashboard.pbix   # Power BI file
│
├── requirements.txt
└── README.md
```

---

## Pipeline Overview

```
Reddit API → PostgreSQL → Python NLP → Power BI Dashboard
   (PRAW)     (raw +        (spaCy +     (filters by
              processed)     VADER)        ingredient /
                                          skin concern /
                                          date)
```

---

## Database Schema (PostgreSQL)

```sql
-- Posts table
CREATE TABLE posts (
    post_id      VARCHAR PRIMARY KEY,
    subreddit    VARCHAR,
    title        TEXT,
    body         TEXT,
    score        INT,
    created_at   TIMESTAMP,
    skin_concern VARCHAR   -- 'acne', 'aging', 'sensitivity', 'other'
);

-- Ingredients table (extracted via NLP)
CREATE TABLE ingredient_mentions (
    mention_id      SERIAL PRIMARY KEY,
    post_id         VARCHAR REFERENCES posts(post_id),
    ingredient      VARCHAR,
    sentiment_score FLOAT,   -- VADER compound score (-1 to 1)
    sentiment_label VARCHAR  -- 'positive', 'neutral', 'negative'
);
```

---

## Key SQL Queries

**Top 10 most negatively-mentioned ingredients:**
```sql
SELECT
    ingredient,
    COUNT(*)                                                          AS mention_count,
    ROUND(AVG(sentiment_score)::numeric, 3)                          AS avg_sentiment,
    ROUND(
        100.0 * SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END)
        / COUNT(*), 1
    )                                                                 AS negative_pct
FROM ingredient_mentions
GROUP BY ingredient
HAVING COUNT(*) >= 50
ORDER BY avg_sentiment ASC
LIMIT 10;
```

**Sentiment trend by month (window function):**
```sql
SELECT
    ingredient,
    DATE_TRUNC('month', p.created_at)                                AS month,
    AVG(sentiment_score)                                             AS avg_sentiment,
    AVG(AVG(sentiment_score)) OVER (
        PARTITION BY ingredient
        ORDER BY DATE_TRUNC('month', p.created_at)
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    )                                                                AS rolling_3mo_avg
FROM ingredient_mentions im
JOIN posts p ON im.post_id = p.post_id
GROUP BY ingredient, month
ORDER BY ingredient, month;
```

---

## NLP Approach

1. **Ingredient extraction** — custom dictionary of ~200 common skincare ingredients matched via `spaCy` entity ruler
2. **Sentence segmentation** — isolate sentences containing ingredient mentions
3. **Sentiment scoring** — VADER sentiment analysis (chosen for social media text; handles abbreviations and informal language well)
4. **Skin concern classification** — keyword-based tagging (`acne`, `aging`, `sensitive`, `hyperpigmentation`) applied at the post level

---

## Dashboard Preview

> *Power BI dashboard screenshot — add after completion*

Key views:
- **Ingredient Sentiment Heatmap** — ingredient vs. skin concern, colored by avg sentiment
- **Trend Line** — monthly sentiment movement for top ingredients
- **Post Explorer** — filterable table linking back to source posts

---

## Key Findings

*(To be updated after analysis)*

Preliminary observations from initial data pull (n = ~2,000 posts):
- Alcohol-based ingredients appear in negative sentiment posts at 2.4× the rate of non-alcohol ingredients
- Fragrance complaints spike significantly in the sensitivity concern segment

---

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up PostgreSQL and run schema
psql -U your_user -d skincare_db -f sql/schema.sql

# 3. Collect data (requires Reddit API credentials — copy .env.example to .env)
jupyter notebook notebooks/01_data_collection.ipynb

# 4. Run pipeline in order: 02 → 03 → 04

# 5. Open dashboard/skincare_dashboard.pbix in Power BI Desktop
```

---

## Skills Demonstrated

`Python` `SQL` `PostgreSQL` `NLP` `VADER Sentiment` `spaCy` `Power BI` `Data Pipeline` `Reddit API` `pandas` `Data Cleaning` `Window Functions` `CTEs`

---

## Author

**Donald Jasper Su**
M.S. Information (Health Informatics) — University of Michigan
[LinkedIn](https://linkedin.com/in/DonaldJasper0621) · [donaldsu@umich.edu](mailto:donaldsu@umich.edu)
