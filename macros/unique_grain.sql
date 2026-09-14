{% test unique_grain(model, columns) %}

{%- set column_list = [] -%}
{%- for col in columns -%}
    {%- do column_list.append(col) -%}
{%- endfor -%}

with validation as (

    select
        {{ column_list | join(', ') }},
        count(*) as row_count
    from {{ model }}
    group by {{ column_list | join(', ') }}
    having count(*) > 1

)

select *
from validation

{% endtest %}
