-- Singular test: validates that elasticity estimation accuracy stays within thresholds.
-- Hard error if mean MAPE > 5%.
-- Per-product: warn at 5%, error at 10%.
-- Returns failing rows (any row returned = test failure).

{{ config(severity='error') }}

with estimates as (
    select
        upc::text as upc,
        true_elasticity,
        estimated_elasticity,
        error_pct,
        abs(error_pct) as abs_error_pct
    from {{ source('synthetic_grocery', 'elasticity_estimates') }}
),

mean_mape as (
    select
        avg(abs_error_pct) as mean_mape,
        count(*) as product_count
    from estimates
),

product_flags as (
    select
        upc,
        true_elasticity,
        estimated_elasticity,
        abs_error_pct,
        case
            when abs_error_pct > 10 then 'ERROR: exceeds 10%'
            when abs_error_pct > 5  then 'WARN: exceeds 5%'
            else 'OK'
        end as product_flag
    from estimates
),

-- Hard error: mean MAPE above 5%
mean_failures as (
    select
        'MEAN_MAPE' as check_type,
        'ALL' as upc,
        null::float as true_elasticity,
        null::float as estimated_elasticity,
        mean_mape as abs_error_pct,
        'ERROR: mean MAPE ' || round(mean_mape::numeric, 2) || '% exceeds 5% threshold (n=' || product_count::text || ')' as failure_reason
    from mean_mape
    where mean_mape > 5
),

-- Per-product hard error: any product above 10%
product_errors as (
    select
        'PRODUCT_ERROR' as check_type,
        upc,
        true_elasticity,
        estimated_elasticity,
        abs_error_pct,
        'ERROR: ' || upc || ' at ' || round(abs_error_pct::numeric, 2) || '% exceeds 10% threshold' as failure_reason
    from product_flags
    where product_flag like 'ERROR%'
)

select * from mean_failures
union all
select * from product_errors
