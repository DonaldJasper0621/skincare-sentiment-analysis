-- Monthly sentiment trend with 3-month rolling average (window function)
SELECT
    im.ingredient,
    DATE_TRUNC('month', p.created_at)           AS month,
    COUNT(*)                                    AS mention_count,
    ROUND(AVG(im.sentiment_score)::numeric, 3)  AS avg_sentiment,
    ROUND(
        AVG(AVG(im.sentiment_score)) OVER (
            PARTITION BY im.ingredient
            ORDER BY DATE_TRUNC('month', p.created_at)
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        )::numeric, 3
    )                                           AS rolling_3mo_avg
FROM ingredient_mentions im
JOIN posts p ON im.post_id = p.post_id
GROUP BY im.ingredient, month
ORDER BY im.ingredient, month;
