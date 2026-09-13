create or replace function public.sync_official_product_catalog(
  p_sync_token text,
  p_products jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, private, extensions, pg_temp
as $$
declare
  expected_hash text;
  item jsonb;
  item_count integer;
  active_count integer;
  archived_count integer;
  item_shopify_id bigint;
  item_handle text;
  item_title text;
  item_price numeric(12, 2);
  item_compare_price numeric(12, 2);
  item_available boolean;
  previous_price numeric(12, 2);
  previous_compare_price numeric(12, 2);
  previous_available boolean;
  previous_found boolean;
begin
  select token_hash
  into expected_hash
  from private.catalog_sync_settings
  where singleton = true;

  if expected_hash is null
    or encode(digest(coalesce(p_sync_token, ''), 'sha256'), 'hex') <> expected_hash
  then
    raise exception 'Invalid catalog sync token';
  end if;

  if jsonb_typeof(p_products) <> 'array' then
    raise exception 'Product payload must be an array';
  end if;

  item_count := jsonb_array_length(p_products);
  if item_count < 300 or item_count > 2000 then
    raise exception 'Unexpected product count: %', item_count;
  end if;

  for item in
    select value from jsonb_array_elements(p_products)
  loop
    item_shopify_id := nullif(item->>'id', '')::bigint;
    item_handle := btrim(coalesce(item->>'handle', ''));
    item_title := btrim(coalesce(item->>'title', ''));
    if item_handle = '' or item_title = '' then
      raise exception 'Product is missing handle or title';
    end if;

    item_price := greatest(
      0,
      coalesce(nullif(item->>'price', '')::numeric, 0)
    );
    item_compare_price := nullif(item->>'compareAtPrice', '')::numeric;
    if item_compare_price is not null and item_compare_price <= item_price then
      item_compare_price := null;
    end if;
    item_available := coalesce((item->>'available')::boolean, false);

    if item_shopify_id is not null then
      update public.price_history history
      set product_handle = item_handle
      from public.official_products product
      where product.shopify_product_id = item_shopify_id
        and product.handle <> item_handle
        and history.product_handle = product.handle;

      update public.official_products
      set handle = item_handle,
          updated_at = now()
      where shopify_product_id = item_shopify_id
        and handle <> item_handle
        and not exists (
          select 1
          from public.official_products target
          where target.handle = item_handle
        );

      delete from public.official_products stale
      where stale.shopify_product_id = item_shopify_id
        and stale.handle <> item_handle;
    end if;

    select
      price_nok,
      compare_at_price_nok,
      available,
      true
    into
      previous_price,
      previous_compare_price,
      previous_available,
      previous_found
    from public.official_products
    where handle = item_handle;

    if not coalesce(previous_found, false)
      or previous_price is distinct from item_price
      or previous_compare_price is distinct from item_compare_price
      or previous_available is distinct from item_available
    then
      insert into public.price_history (
        product_handle,
        article_number,
        price_nok,
        compare_at_price_nok,
        available,
        source_url
      )
      values (
        item_handle,
        nullif(btrim(coalesce(item->>'articleNumber', '')), ''),
        item_price,
        item_compare_price,
        item_available,
        btrim(coalesce(item->>'url', ''))
      );
    end if;

    insert into public.official_products (
      shopify_product_id,
      handle,
      article_number,
      title,
      description,
      price_nok,
      compare_at_price_nok,
      available,
      image_url,
      images,
      series,
      tags,
      source_url,
      in_official_catalog,
      first_seen_at,
      last_seen_at,
      removed_at,
      updated_at
    )
    values (
      item_shopify_id,
      item_handle,
      nullif(btrim(coalesce(item->>'articleNumber', '')), ''),
      item_title,
      nullif(btrim(coalesce(item->>'description', '')), ''),
      item_price,
      item_compare_price,
      item_available,
      nullif(btrim(coalesce(item->>'image', '')), ''),
      case
        when jsonb_typeof(item->'images') = 'array' then item->'images'
        else '[]'::jsonb
      end,
      nullif(btrim(coalesce(item->>'series', '')), ''),
      case
        when jsonb_typeof(item->'tags') = 'array' then item->'tags'
        else '[]'::jsonb
      end,
      btrim(coalesce(item->>'url', '')),
      true,
      now(),
      now(),
      null,
      now()
    )
    on conflict (handle) do update
    set shopify_product_id = excluded.shopify_product_id,
        article_number = excluded.article_number,
        title = excluded.title,
        description = excluded.description,
        price_nok = excluded.price_nok,
        compare_at_price_nok = excluded.compare_at_price_nok,
        available = excluded.available,
        image_url = excluded.image_url,
        images = excluded.images,
        series = excluded.series,
        tags = excluded.tags,
        source_url = excluded.source_url,
        in_official_catalog = true,
        last_seen_at = now(),
        removed_at = null,
        updated_at = now();
  end loop;

  update public.official_products archived
  set in_official_catalog = false,
      removed_at = coalesce(archived.removed_at, now()),
      updated_at = now()
  where archived.in_official_catalog = true
    and not exists (
      select 1
      from jsonb_array_elements(p_products) current_item
      where btrim(coalesce(current_item->>'handle', '')) = archived.handle
    );

  select count(*) filter (where in_official_catalog),
         count(*) filter (where not in_official_catalog)
  into active_count, archived_count
  from public.official_products;

  return jsonb_build_object(
    'received', item_count,
    'active', active_count,
    'archived', archived_count
  );
end;
$$;

revoke all on function public.sync_official_product_catalog(text, jsonb)
from public;

grant execute on function public.sync_official_product_catalog(text, jsonb)
to anon, authenticated;
