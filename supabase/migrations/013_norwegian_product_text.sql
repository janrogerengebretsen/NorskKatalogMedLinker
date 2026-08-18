alter table public.official_products
  add column if not exists title_no text,
  add column if not exists description_no text,
  add column if not exists translation_source_language text,
  add column if not exists translation_source_title text,
  add column if not exists translation_source_description text,
  add column if not exists translated_at timestamptz;

create or replace function public.invalidate_changed_product_translation()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
begin
  if new.title is distinct from old.title
    or new.description is distinct from old.description
  then
    new.title_no := null;
    new.description_no := null;
    new.translation_source_language := null;
    new.translation_source_title := null;
    new.translation_source_description := null;
    new.translated_at := null;
  end if;
  return new;
end;
$$;

drop trigger if exists official_products_invalidate_translation
on public.official_products;

create trigger official_products_invalidate_translation
before update of title, description on public.official_products
for each row
execute function public.invalidate_changed_product_translation();

create or replace function public.save_official_product_translation(
  p_sync_token text,
  p_handle text,
  p_source_title text,
  p_source_description text,
  p_title_no text,
  p_description_no text,
  p_source_language text
)
returns boolean
language plpgsql
security definer
set search_path = public, private, extensions, pg_temp
as $$
declare
  expected_hash text;
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

  update public.official_products
  set title_no = nullif(btrim(coalesce(p_title_no, '')), ''),
      description_no = nullif(btrim(coalesce(p_description_no, '')), ''),
      translation_source_language = nullif(btrim(coalesce(p_source_language, '')), ''),
      translation_source_title = coalesce(p_source_title, ''),
      translation_source_description = coalesce(p_source_description, ''),
      translated_at = now()
  where handle = btrim(coalesce(p_handle, ''))
    and title = coalesce(p_source_title, '')
    and coalesce(description, '') = coalesce(p_source_description, '');

  return found;
end;
$$;

revoke all on function public.save_official_product_translation(
  text, text, text, text, text, text, text
) from public;

grant execute on function public.save_official_product_translation(
  text, text, text, text, text, text, text
) to anon, authenticated;

comment on column public.official_products.title_no is
  'Norwegian product title from the official storefront or the translation fallback.';

comment on column public.official_products.description_no is
  'Norwegian product description from the official storefront or the translation fallback.';
