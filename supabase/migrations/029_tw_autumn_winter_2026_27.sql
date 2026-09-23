insert into public.products (product_key, title, description)
values (
  'tw-host-vinter-2026-27',
  'TWHøstVinter202627',
  'Digital høst- og vinterkatalog 2026-2027 med personlige produktlenker.'
)
on conflict (product_key) do update
set
  title = excluded.title,
  description = excluded.description,
  is_active = true,
  updated_at = now();

insert into public.consultant_product_access (consultant_id, product_key)
select id, 'tw-host-vinter-2026-27'
from public.consultants
where reference_code = 'LISBETHOVERBYE'
on conflict (consultant_id, product_key) do update
set is_active = true, updated_at = now();
