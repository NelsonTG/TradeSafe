{{ config(
    materialized='incremental',
    unique_key=['ticker', 'trade_date']
) }}

select
    rawdata:ticker::string                                       as ticker,
    regexp_substr(fileName, 'dt=([^/]*)', 1, 1, 'e', 1)::date    as trade_date,
    rawdata:open::decimal(18,4)                                  as open_price,
    rawdata:high::decimal(18,4)                                  as high_price,
    rawdata:low::decimal(18,4)                                   as low_price,
    rawdata:close::decimal(18,4)                                 as close_price,
    rawdata:volume::decimal(24,6)                                as volume
from {{ source('data', 'dailydata') }}

{% if is_incremental() %}
where regexp_substr(fileName, 'dt=([^/]*)', 1, 1, 'e', 1)::date > (select max(trade_date) from {{ this }})
{% endif %}