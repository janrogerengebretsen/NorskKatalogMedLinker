alter table public.party_orders
  add column if not exists customer_postal_code text,
  add column if not exists customer_city text,
  add column if not exists customer_country text;

comment on column public.party_orders.customer_address is
  'Kundens gateadresse eller leveringsadresse.';

comment on column public.party_orders.customer_postal_code is
  'Kundens postnummer.';

comment on column public.party_orders.customer_city is
  'Kundens poststed/by.';

comment on column public.party_orders.customer_country is
  'Kundens land. Valgfritt felt for løsningen.';
