alter table public.inventory
  add column source_type text not null default 'official'
    check (source_type in ('official', 'custom')),
  add column product_name text,
  add column description text,
  add column image_url text,
  add column source_product_url text,
  add column category text,
  add column is_active boolean not null default true,
  add column created_at timestamptz not null default now();

update public.inventory
set product_name = coalesce(
  nullif(product_name, ''),
  nullif(article_number, ''),
  product_handle
);

alter table public.inventory
  alter column product_name set not null;

alter table public.order_requests
  add column order_source text not null default 'consultant_inventory'
    check (order_source in ('consultant_inventory'));

alter table public.order_items
  add column inventory_item_id uuid references public.inventory(id) on delete set null;

drop policy if exists "Public can read available inventory" on public.inventory;

create policy "Public can read consultant catalog inventory"
on public.inventory for select
to anon, authenticated
using (
  is_active = true
  and is_for_sale = true
  and quantity > 0
  and sale_price_nok is not null
  and exists (
    select 1
    from public.consultants
    where id = consultant_id
      and status = 'active'
      and public_listing = true
  )
);

create or replace view public.public_consultant_inventory
with (security_invoker = true)
as
select
  inventory.id,
  inventory.consultant_id,
  consultants.reference_code,
  consultants.display_name as consultant_name,
  inventory.source_type,
  inventory.product_handle,
  inventory.article_number,
  inventory.product_name,
  inventory.description,
  inventory.image_url,
  inventory.source_product_url,
  inventory.category,
  inventory.quantity,
  inventory.sale_price_nok,
  inventory.updated_at
from public.inventory
join public.consultants on consultants.id = inventory.consultant_id
where inventory.is_active = true
  and inventory.is_for_sale = true
  and inventory.quantity > 0
  and inventory.sale_price_nok is not null
  and consultants.status = 'active'
  and consultants.public_listing = true;

grant select on public.public_consultant_inventory to anon, authenticated;

create or replace function public.submit_consultant_inventory_order(
  p_reference_code text,
  p_customer jsonb,
  p_items jsonb
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  selected_consultant public.consultants%rowtype;
  new_order_id uuid;
  customer_name text;
  customer_email text;
  customer_phone text;
  customer_message text;
  item jsonb;
  selected_inventory public.inventory%rowtype;
  requested_quantity integer;
begin
  customer_name := trim(coalesce(p_customer->>'name', ''));
  customer_email := nullif(trim(coalesce(p_customer->>'email', '')), '');
  customer_phone := nullif(trim(coalesce(p_customer->>'phone', '')), '');
  customer_message := nullif(trim(coalesce(p_customer->>'message', '')), '');

  if char_length(customer_name) < 2 or char_length(customer_name) > 120 then
    raise exception 'Oppgi kundens navn.';
  end if;

  if customer_email is null and customer_phone is null then
    raise exception 'Oppgi e-postadresse eller telefonnummer.';
  end if;

  if jsonb_typeof(p_items) <> 'array'
    or jsonb_array_length(p_items) < 1
    or jsonb_array_length(p_items) > 30 then
    raise exception 'Bestillingen må inneholde mellom 1 og 30 varer.';
  end if;

  select *
  into selected_consultant
  from public.consultants
  where reference_code = upper(trim(p_reference_code))
    and status = 'active'
    and public_listing = true;

  if not found then
    raise exception 'Konsulenten finnes ikke eller er ikke aktiv.';
  end if;

  insert into public.order_requests (
    consultant_id,
    customer_name,
    customer_email,
    customer_phone,
    customer_message,
    order_source
  )
  values (
    selected_consultant.id,
    customer_name,
    customer_email,
    customer_phone,
    customer_message,
    'consultant_inventory'
  )
  returning id into new_order_id;

  for item in select * from jsonb_array_elements(p_items)
  loop
    requested_quantity := greatest(1, least(99, coalesce((item->>'quantity')::integer, 1)));

    select *
    into selected_inventory
    from public.inventory
    where id = (item->>'inventory_id')::uuid
      and consultant_id = selected_consultant.id
      and is_active = true
      and is_for_sale = true
      and quantity >= requested_quantity
      and sale_price_nok is not null;

    if not found then
      raise exception 'En vare er utsolgt eller tilhører ikke denne konsulenten.';
    end if;

    insert into public.order_items (
      order_request_id,
      inventory_item_id,
      product_handle,
      article_number,
      product_name,
      quantity,
      observed_price_nok
    )
    values (
      new_order_id,
      selected_inventory.id,
      selected_inventory.product_handle,
      selected_inventory.article_number,
      selected_inventory.product_name,
      requested_quantity,
      selected_inventory.sale_price_nok
    );
  end loop;

  return new_order_id;
end;
$$;

revoke all on function public.submit_consultant_inventory_order(text, jsonb, jsonb)
from public;
grant execute on function public.submit_consultant_inventory_order(text, jsonb, jsonb)
to anon, authenticated;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'consultant-products',
  'consultant-products',
  true,
  5242880,
  array['image/jpeg', 'image/png', 'image/webp']
)
on conflict (id) do update
set public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "Public reads consultant product images" on storage.objects;
create policy "Public reads consultant product images"
on storage.objects for select
using (bucket_id = 'consultant-products');

drop policy if exists "Consultants upload own product images" on storage.objects;
create policy "Consultants upload own product images"
on storage.objects for insert
to authenticated
with check (
  bucket_id = 'consultant-products'
  and public.owns_consultant(((storage.foldername(name))[1])::uuid)
);

drop policy if exists "Consultants update own product images" on storage.objects;
create policy "Consultants update own product images"
on storage.objects for update
to authenticated
using (
  bucket_id = 'consultant-products'
  and public.owns_consultant(((storage.foldername(name))[1])::uuid)
)
with check (
  bucket_id = 'consultant-products'
  and public.owns_consultant(((storage.foldername(name))[1])::uuid)
);

drop policy if exists "Consultants delete own product images" on storage.objects;
create policy "Consultants delete own product images"
on storage.objects for delete
to authenticated
using (
  bucket_id = 'consultant-products'
  and public.owns_consultant(((storage.foldername(name))[1])::uuid)
);
