insert into public.products (product_key, title, description)
values (
  'party',
  'Party',
  'Digital og fysisk party-løsning med påmelding, fokusprodukter og bestillinger.'
)
on conflict (product_key) do update
set
  title = excluded.title,
  description = excluded.description;

insert into public.consultant_product_access (consultant_id, product_key)
select id, 'party'
from public.consultants
where reference_code = 'LISBETHOVERBYE'
on conflict (consultant_id, product_key) do update
set is_active = true, updated_at = now();
