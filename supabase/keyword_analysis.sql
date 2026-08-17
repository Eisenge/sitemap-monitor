create table if not exists public.page_insights(
 website_id uuid not null references public.websites(id) on delete cascade,
 user_id uuid not null references auth.users(id) on delete cascade,
 url text not null,
 url_hash text not null,
 title text,
 meta_description text,
 h1 text,
 language text,
 keywords jsonb not null default '[]'::jsonb,
 analyzed_at timestamptz not null default now(),
 error text,
 primary key(website_id,url_hash)
);
alter table public.page_insights enable row level security;
drop policy if exists insights_owner on public.page_insights;
create policy insights_owner on public.page_insights for select using(auth.uid()=user_id);
create index if not exists insights_time on public.page_insights(user_id,analyzed_at desc);
