WITH quote_metrics AS (
    SELECT
        card_id,
        COUNT(*) AS offers,
        SUM(clicked) AS clicks,
        AVG(apr) AS avg_apr,
        AVG(likelihood) AS avg_likelihood,
        AVG(apr_rank) AS avg_apr_rank,
        AVG(likelihood_rank) AS avg_likelihood_rank
    FROM quotes
    GROUP BY card_id
)

SELECT
    q.card_id,
    q.offers,
    q.clicks,

    q.clicks * 1.0
        / NULLIF(q.offers, 0)
        AS click_through_rate,

    s.sales,

    s.sales * 1.0
        / NULLIF(q.clicks, 0)
        AS click_to_sale_rate,

    s.revenue,

    s.revenue
        / NULLIF(q.clicks, 0)
        AS revenue_per_click,

    s.revenue
        / NULLIF(q.offers, 0)
        AS revenue_per_offer,

    s.revenue
        / NULLIF(s.sales, 0)
        AS revenue_per_sale,

    q.avg_apr,
    q.avg_likelihood,
    q.avg_apr_rank,
    q.avg_likelihood_rank

FROM quote_metrics q

LEFT JOIN sales s
    ON q.card_id = s.card_id

ORDER BY q.clicks DESC;