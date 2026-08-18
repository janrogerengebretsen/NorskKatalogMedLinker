create schema if not exists private;
revoke all on schema private from public;

create table if not exists private.catalog_sync_settings (
  singleton boolean primary key default true check (singleton),
  token_hash text not null,
  updated_at timestamptz not null default now()
);

insert into private.catalog_sync_settings (singleton, token_hash)
values (
  true,
  '7b343f0da800725d257fc0b7361d3f288719b787a5b7c4e8699b75ccdc0a74ca'
)
on conflict (singleton) do update
set token_hash = excluded.token_hash,
    updated_at = now();

create table if not exists public.official_products (
  id uuid primary key default gen_random_uuid(),
  shopify_product_id bigint,
  handle text not null unique,
  article_number text,
  title text not null,
  description text,
  price_nok numeric(12, 2) not null default 0 check (price_nok >= 0),
  compare_at_price_nok numeric(12, 2)
    check (compare_at_price_nok is null or compare_at_price_nok >= 0),
  available boolean not null default false,
  image_url text,
  images jsonb not null default '[]'::jsonb
    check (jsonb_typeof(images) = 'array'),
  series text,
  tags jsonb not null default '[]'::jsonb
    check (jsonb_typeof(tags) = 'array'),
  source_url text not null,
  in_official_catalog boolean not null default true,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  removed_at timestamptz,
  updated_at timestamptz not null default now()
);

create unique index if not exists official_products_shopify_id
  on public.official_products (shopify_product_id)
  where shopify_product_id is not null;

create index if not exists official_products_catalog_title
  on public.official_products (in_official_catalog desc, title);

create index if not exists official_products_series
  on public.official_products (series)
  where series is not null;

alter table public.official_products enable row level security;

drop policy if exists "Public reads official product archive"
on public.official_products;

create policy "Public reads official product archive"
on public.official_products for select
to anon, authenticated
using (true);

revoke all on public.official_products from public;
grant select on public.official_products to anon, authenticated;

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
      nullif(item->>'id', '')::bigint,
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

comment on table public.official_products is
  'Persistent archive of official Tupperware products. Products remain after removal from the official shop.';

comment on column public.official_products.in_official_catalog is
  'True while the product is present in the current Norwegian Tupperware product feed.';
