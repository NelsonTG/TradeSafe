select
    rawdata:ticker::string      as ticker,
    rawdata:name::string        as company_name,
    rawdata:market_cap::decimal as market_cap,
    rawdata:active::boolean as active,
    rawdata:list_date::date as list_date,
    rawdata:total_employees::int as total_employees,
    rawdata:description::string as description,
    regexp_substr(rawdata:address::string, $$city='([^']*)'$$, 1, 1, 'e', 1) as city,
    regexp_substr(rawdata:address::string, $$state='([^']*)'$$, 1, 1, 'e', 1) as state,
    regexp_substr(rawdata:address::string, $$postal_code='([^']*)'$$, 1, 1, 'e', 1) as postal_code
from {{ source('data', 'INITIAL') }}