
-- ============================================
-- GOLD LAYER: BUSINESS REPORTING
-- ============================================


-- 1. MONTHLY SERVICE REQUEST VOLUME

CREATE OR REPLACE VIEW gold_monthly_requests AS
SELECT
    DATE_TRUNC('month', requested_datetime)::DATE AS request_month,

    COUNT(*) AS total_requests,

    COUNT(*) FILTER (
        WHERE status_description = 'Closed'
    ) AS closed_requests,

    COUNT(*) FILTER (
        WHERE status_description = 'Open'
    ) AS open_requests

FROM service_requests

WHERE requested_datetime IS NOT NULL

GROUP BY request_month;



-- 2. SERVICE REQUESTS BY NEIGHBORHOOD

CREATE OR REPLACE VIEW gold_neighborhood_requests AS
SELECT
    COALESCE(
        NULLIF(TRIM(analysis_neighborhood), ''),
        'Unknown'
    ) AS neighborhood,

    COUNT(*) AS total_requests,

    COUNT(*) FILTER (
        WHERE status_description = 'Closed'
    ) AS closed_requests,

    ROUND(
        AVG(resolution_hours) FILTER (
            WHERE status_description = 'Closed'
              AND resolution_hours >= 0
        )::NUMERIC,
        2
    ) AS avg_resolution_hours

FROM service_requests

GROUP BY neighborhood;



-- 3. SERVICE REQUESTS BY CATEGORY

CREATE OR REPLACE VIEW gold_service_categories AS
SELECT
    COALESCE(
        NULLIF(TRIM(service_name), ''),
        'Unknown'
    ) AS service_category,

    COUNT(*) AS total_requests,

    COUNT(*) FILTER (
        WHERE status_description = 'Closed'
    ) AS closed_requests,

    ROUND(
        AVG(resolution_hours) FILTER (
            WHERE status_description = 'Closed'
              AND resolution_hours >= 0
        )::NUMERIC,
        2
    ) AS avg_resolution_hours

FROM service_requests

GROUP BY service_category;
