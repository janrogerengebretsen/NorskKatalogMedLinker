insert into public.products (product_key, title, description)
values (
  'maanedstilbud',
  'Månedens tilbudskatalog',
  'Abonnement på den nyeste månedskatalogen med norske tekster og personlige produktlenker.'
)
on conflict (product_key) do update
set
  title = excluded.title,
  description = excluded.description,
  is_active = true,
  updated_at = now();

update public.consultant_product_access
set is_active = false, updated_at = now()
where product_key = 'maanedstilbud'
  and consultant_id not in (
    select id
    from public.consultants
    where reference_code in ('LISBETHOVERBYE', 'VIVIANKONGSVOLD')
  );

insert into public.consultant_product_access (consultant_id, product_key, is_active)
select id, 'maanedstilbud', true
from public.consultants
where reference_code in ('LISBETHOVERBYE', 'VIVIANKONGSVOLD')
on conflict (consultant_id, product_key) do update
set is_active = true, updated_at = now();
