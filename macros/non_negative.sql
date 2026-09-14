{% test non_negative(model, column_name) %}

with validation as (

    select
        {{ column_name }} as tested_value
    from {{ model }}
    where {{ column_name }} < 0

)

select *
from validation

{% endtest %}
