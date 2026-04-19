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
| Data Collection | Kaggle (Sephora Reviews dataset) · Reddit `.json` fallback |
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

*Based on 9,729 ingredient mentions extracted from 50,000 Sephora product reviews.*

### Most Negatively-Mentioned Ingredients (≥50 mentions)

| Ingredient | Mentions | Avg Sentiment | Negative Rate |
|---|---|---|---|
| Benzoyl Peroxide | 56 | 0.413 | **23.2%** |
| Alcohol | 202 | 0.434 | **15.3%** |
| Tretinoin | 75 | 0.604 | 8.0% |
| Salicylic Acid | 195 | 0.604 | 11.3% |
| BHA | 171 | 0.607 | 10.5% |

### Sentiment by Skin Concern

Acne-focused posts generated significantly more negative sentiment (11.1% negative rate) compared to aging-focused posts (5.2%) — suggesting acne treatments are perceived as harsher or more irritating.

| Skin Concern | Posts | Avg Sentiment | Negative Rate |
|---|---|---|---|
| Acne | 1,089 | 0.588 | 11.1% |
| Sensitivity | 998 | 0.628 | 8.5% |
| Other | 3,442 | 0.663 | 5.8% |
| Aging | 909 | 0.725 | 5.2% |
| Hyperpigmentation | 172 | 0.764 | 3.4% |

### Actionable Insight: Retinol Sentiment Diverges by Use Case

Retinol's negative rate is **2.7× higher** in acne contexts (11.5%) vs. aging contexts (5.7%) — suggesting formulation or communication strategy should differ by target concern. Alcohol shows similar divergence: 17.5% negative in sensitivity posts vs. 7.7% in aging posts.

---

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 2. Set up PostgreSQL and run schema
psql -U your_user -d skincare_db -f sql/schema.sql

# 3a. Collect data — Option A: Kaggle (recommended, no API wait)
#     Place kaggle.json in ~/.kaggle/ then run:
jupyter notebook notebooks/01_data_collection.ipynb   # run Option A cells

# 3b. Collect data — Option B: Reddit JSON (no API key needed)
#     Run Option B cells in the same notebook
#     (~1,000 posts, respects 1 req/sec rate limit automatically)

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
