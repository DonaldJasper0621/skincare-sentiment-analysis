-- ============================================================
-- Skincare Sentiment Analysis — PostgreSQL Schema
-- Run against skincare_db (already created separately)
-- ============================================================

-- Posts collected from Reddit / Sephora reviews
CREATE TABLE posts (
    post_id      VARCHAR PRIMARY KEY,
    subreddit    VARCHAR      NOT NULL DEFAULT 'SkincareAddiction',
    title        TEXT,
    body         TEXT,
    score        INT,
    num_comments INT,
    created_at   TIMESTAMP    NOT NULL,
    skin_concern VARCHAR      CHECK (skin_concern IN ('acne', 'aging', 'sensitivity', 'hyperpigmentation', 'other')),
    collected_at TIMESTAMP    DEFAULT NOW()
);

-- Ingredient mentions extracted via NLP
CREATE TABLE ingredient_mentions (
    mention_id      SERIAL PRIMARY KEY,
    post_id         VARCHAR      REFERENCES posts(post_id) ON DELETE CASCADE,
    ingredient      VARCHAR      NOT NULL,
    sentence        TEXT,                            -- source sentence for context
    sentiment_score FLOAT,                           -- VADER compound score (-1.0 to 1.0)
    sentiment_label VARCHAR      CHECK (sentiment_label IN ('positive', 'neutral', 'negative'))
);

-- Indexes for query performance
CREATE INDEX idx_posts_skin_concern   ON posts(skin_concern);
CREATE INDEX idx_posts_created_at     ON posts(created_at);
CREATE INDEX idx_mentions_ingredient  ON ingredient_mentions(ingredient);
CREATE INDEX idx_mentions_sentiment   ON ingredient_mentions(sentiment_label);
