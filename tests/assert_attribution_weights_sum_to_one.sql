-- Singular test: for every account_id in int_attribution_paths, the attribution
-- weight columns must each sum to 1.0 (linear allowed a small float tolerance).

with weight_sums as (

    select
        account_id,
        sum(first_touch_weight) as total_first_touch_weight,
        sum(last_touch_weight) as total_last_touch_weight,
        sum(linear_weight) as total_linear_weight
    from {{ ref('int_attribution_paths') }}
    group by account_id

),

violations as (

    select
        account_id,
        total_first_touch_weight,
        total_last_touch_weight,
        total_linear_weight
    from weight_sums
    where
        abs(total_first_touch_weight - 1.0) > 0.001
        or abs(total_last_touch_weight - 1.0) > 0.001
        or total_linear_weight < 0.999
        or total_linear_weight > 1.001

)

select *
from violations
