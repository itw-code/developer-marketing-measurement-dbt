select
    base_currency,
    quote_currency,
    cast(rate as double) as exchange_rate,
    cast(fetched_at as timestamp) as fetched_at,
    case
        when quote_currency = 'USD' then 1.0
        else 1.0 / nullif(cast(rate as double), 0)
    end as rate_to_usd
from {{ ref('raw_fx_rates') }}
