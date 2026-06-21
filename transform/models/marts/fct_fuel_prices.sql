{{ config(materialized='incremental') }}

select
    node_id,
    trading_name,
    brand_name,
    fuel_type,
    price_pence,
    price_last_updated,
    price_change_effective_timestamp,
    loaded_at,
    is_motorway_service_station,
    is_supermarket_service_station,
    city,
    county,
    country,
    postcode,
    latitude,
    longitude
from {{ ref('int_prices_with_station') }}

{% if is_incremental() %}
where loaded_at > (
    select coalesce(max(loaded_at), '1970-01-01'::timestamptz) from {{ this }}
)
{% endif %}
