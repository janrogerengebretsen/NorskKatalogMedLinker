insert into public.products (product_key, title, description)
values (
  'maanedstilbud',
  'Siste månedstilbud',
  'Abonnement på den nyeste månedskatalogen med aktuelle tilbud og personlige produktlenker.'
)
on conflict (product_key) do update
set
  title = excluded.title,
  description = excluded.description,
  is_active = true,
  updated_at = now();

insert into public.consultant_product_access (consultant_id, product_key)
select id, 'maanedstilbud'
from public.consultants
where reference_code = 'LISBETHOVERBYE'
on conflict (consultant_id, product_key) do update
set is_active = true, updated_at = now();
