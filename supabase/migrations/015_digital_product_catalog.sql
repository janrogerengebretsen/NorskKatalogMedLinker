update public.products
set title = 'Digital Produktkatalog',
    description = 'Digital produktkatalog med søk og personlige produktlenker.',
    is_active = true,
    updated_at = now()
where product_key = 'norsk-produktkatalog';

insert into public.consultant_product_access (consultant_id, product_key)
select id, 'norsk-produktkatalog'
from public.consultants
where reference_code in ('LISBETHOVERBYE', 'VIVIANKONGSVOLD')
on conflict (consultant_id, product_key)
do update set is_active = true, updated_at = now();
