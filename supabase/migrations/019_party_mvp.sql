create table if not exists public.party_events (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  party_type text not null default 'combined'
    check (party_type in ('combined', 'digital', 'physical')),
  starts_at timestamptz,
  ends_at timestamptz,
  host_mode text not null default 'manual'
    check (host_mode in ('manual', 'consultant', 'guest')),
  host_name text,
  location text,
  message text,
  host_intro text,
  video_url text,
  vipps_message text,
  featured_product_ids jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (ends_at is null or starts_at is null or ends_at >= starts_at)
);

create table if not exists public.party_orders (
  id uuid primary key default gen_random_uuid(),
  party_id uuid not null references public.party_events(id) on delete cascade,
  customer_name text not null,
  status text not null default 'Ny',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.party_order_lines (
  id uuid primary key default gen_random_uuid(),
  party_order_id uuid not null references public.party_orders(id) on delete cascade,
  product_id text,
  product_name text not null,
  article_number text,
  quantity integer not null default 1 check (quantity > 0),
  observed_price_nok numeric(12, 2) check (observed_price_nok is null or observed_price_nok >= 0)
);

create trigger party_events_set_updated_at
before update on public.party_events
for each row execute function public.set_updated_at();

create trigger party_orders_set_updated_at
before update on public.party_orders
for each row execute function public.set_updated_at();

alter table public.party_events enable row level security;
alter table public.party_orders enable row level security;
alter table public.party_order_lines enable row level security;

drop policy if exists "Public can read party events" on public.party_events;
create policy "Public can read party events"
on public.party_events for select
using (true);

drop policy if exists "Public can manage party events for MVP" on public.party_events;
create policy "Public can manage party events for MVP"
on public.party_events for all
to anon, authenticated
using (true)
with check (true);

drop policy if exists "Public can read party orders for MVP" on public.party_orders;
create policy "Public can read party orders for MVP"
on public.party_orders for select
to anon, authenticated
using (true);

drop policy if exists "Public can create party orders for MVP" on public.party_orders;
create policy "Public can create party orders for MVP"
on public.party_orders for insert
to anon, authenticated
with check (true);

drop policy if exists "Public can update party orders for MVP" on public.party_orders;
create policy "Public can update party orders for MVP"
on public.party_orders for update
to anon, authenticated
using (true)
with check (true);

drop policy if exists "Public can delete party orders for MVP" on public.party_orders;
create policy "Public can delete party orders for MVP"
on public.party_orders for delete
to anon, authenticated
using (true);

drop policy if exists "Public can read party order lines for MVP" on public.party_order_lines;
create policy "Public can read party order lines for MVP"
on public.party_order_lines for select
to anon, authenticated
using (true);

drop policy if exists "Public can create party order lines for MVP" on public.party_order_lines;
create policy "Public can create party order lines for MVP"
on public.party_order_lines for insert
to anon, authenticated
with check (true);

drop policy if exists "Public can delete party order lines for MVP" on public.party_order_lines;
create policy "Public can delete party order lines for MVP"
on public.party_order_lines for delete
to anon, authenticated
using (true);

grant select, insert, update, delete on public.party_events to anon, authenticated;
grant select, insert, update, delete on public.party_orders to anon, authenticated;
grant select, insert, update, delete on public.party_order_lines to anon, authenticated;

comment on table public.party_events is
  'MVP-lagring for party opprettet av konsulenter. Brukes av /party i NorskKatalogMedLinker.';

comment on table public.party_orders is
  'En enkel bestilling per kunde per innsending til partyet. Praktisk for konsulenten ved videre registrering hos Tupperware.';

comment on table public.party_order_lines is
  'Produktlinjer for party-bestillinger. Kun nødvendig ordreinformasjon lagres.';
