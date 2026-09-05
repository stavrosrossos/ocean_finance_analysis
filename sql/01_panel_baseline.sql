WITH application_metrics AS (
    SELECT
        application_id,
        COUNT(*) AS offers_received,
        SUM(clicked) AS clicks
    FROM quotes
    GROUP BY application_id
),

quote_totals AS (
    SELECT
        COUNT(*) AS total_offers,
        SUM(clicked) AS total_clicks
    FROM quotes
),

application_totals AS (
    SELECT
        COUNT(*) AS total_applications,
        SUM(
            CASE
                WHEN clicks > 0 THEN 1
                ELSE 0
            END
        ) AS applications_with_click
    FROM application_metrics
),

sales_totals AS (
    SELECT
        SUM(sales) AS total_sales,
        SUM(revenue) AS total_revenue
    FROM sales
)

SELECT
    a.total_applications,
    q.total_offers,
    a.applications_with_click,
    q.total_clicks,
    s.total_sales,
    s.total_revenue,

    a.applications_with_click * 1.0
        / a.total_applications
        AS application_clickout_rate,

    q.total_clicks * 1.0
        / q.total_offers
        AS offer_click_through_rate,

    s.total_sales * 1.0
        / q.total_clicks
        AS click_to_sale_rate,

    s.total_revenue
        / q.total_clicks
        AS revenue_per_click,

    s.total_revenue
        / a.total_applications
        AS revenue_per_application,

    s.total_sales * 100.0
        / a.total_applications
        AS sales_per_100_applications

FROM application_totals a
CROSS JOIN quote_totals q
CROSS JOIN sales_totals s;