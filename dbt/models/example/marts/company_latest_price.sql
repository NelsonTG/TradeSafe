{{ config(materialized='table') }}

with latest_price as (
    select *
    from {{ ref('stg_prices') }}
    qualify row_number() over (partition by ticker order by trade_date desc) = 1
)

select
    c.ticker,
    c.company_name,
    c.market_cap,
    c.city,
    c.state,
    p.trade_date  as price_date,
    p.close_price,
    p.volume
from {{ ref('stg_initial') }} c
left join latest_price p on c.ticker = p.ticker