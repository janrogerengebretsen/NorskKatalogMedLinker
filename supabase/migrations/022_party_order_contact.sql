alter table public.party_orders
  add column if not exists customer_email text,
  add column if not exists customer_phone text,
  add column if not exists customer_address text;

comment on column public.party_orders.customer_email is
  'Kundens e-post for oppfølging av party-bestillingen.';

comment on column public.party_orders.customer_phone is
  'Kundens telefonnummer for oppfølging av party-bestillingen.';

comment on column public.party_orders.customer_address is
  'Kundens adresse slik den ble oppgitt ved bestilling.';
