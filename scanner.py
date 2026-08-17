import hashlib, os, sys, time, xml.etree.ElementTree as ET
from urllib.parse import urljoin
import requests

BASE=os.environ.get('SUPABASE_URL','').rstrip('/')
KEY=os.environ.get('SUPABASE_SERVICE_ROLE_KEY','')
HEAD={'apikey':KEY,'Content-Type':'application/json','Prefer':'return=representation'}
# Legacy service_role keys are JWTs and may also be used as a Bearer token.
# New sb_secret_ keys authenticate through the apikey header only.
if KEY.count('.') == 2:
 HEAD['Authorization']=f'Bearer {KEY}'
UA={'User-Agent':'SitemapMonitor/1.0 (+GitHub Actions)'}

def api(path,method='GET',data=None,params=None):
 r=requests.request(method,f'{BASE}/rest/v1/{path}',headers=HEAD,json=data,params=params,timeout=30); r.raise_for_status()
 return r.json() if r.content else None

def get(url):
 r=requests.get(url,headers=UA,timeout=int(os.getenv('HTTP_TIMEOUT','25')),allow_redirects=True); r.raise_for_status(); return r

def discover(home):
 robots=urljoin(home.rstrip('/')+'/', 'robots.txt'); text=''; maps=[]
 try:
  text=get(robots).text
  maps=[line.split(':',1)[1].strip() for line in text.splitlines() if line.lower().startswith('sitemap:') and ':' in line]
 except requests.RequestException: pass
 if not maps: maps=[urljoin(home.rstrip('/')+'/',x) for x in ('sitemap.xml','sitemap_index.xml')]
 return text,maps

def crawl(initial):
 pending=list(initial); seen=set(); urls=set(); errors=[]
 while pending:
  loc=pending.pop(0)
  if loc in seen: continue
  if len(seen)>=int(os.getenv('MAX_SITEMAPS','500')): raise RuntimeError('Sitemap 数量超过安全限制')
  seen.add(loc)
  try:
   root=ET.fromstring(get(loc).content); tag=root.tag.rsplit('}',1)[-1].lower()
   items=[(x.text or '').strip() for x in root.iter() if x.tag.rsplit('}',1)[-1].lower()=='loc' and x.text]
   if tag=='sitemapindex': pending.extend(urljoin(loc,x) for x in items)
   elif tag=='urlset': urls.update(items)
   else: errors.append(f'未知 XML 根节点: {loc}')
  except (requests.RequestException,ET.ParseError) as e: errors.append(f'{loc}: {e}')
 if not urls and errors: raise RuntimeError('; '.join(errors[:3]))
 return urls,errors

def notify(msg):
 token=os.getenv('TELEGRAM_BOT_TOKEN'); chat=os.getenv('TELEGRAM_CHAT_ID')
 if token and chat: requests.post(f'https://api.telegram.org/bot{token}/sendMessage',json={'chat_id':chat,'text':msg[:4000]},timeout=15).raise_for_status()

def scan(site):
 now=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()); robots,maps=discover(site['home_url'])
 rh=hashlib.sha256(robots.encode()).hexdigest(); robots_changed=bool(site.get('robots_hash') and site['robots_hash']!=rh)
 if site.get('sitemap_url'): maps=[site['sitemap_url']]
 urls,warnings=crawl(maps)
 old=api('url_snapshots',params={'website_id':f"eq.{site['id']}",'active':'eq.true','select':'url,url_hash'}) or []
 old_urls={x['url'] for x in old}; added=urls-old_urls; removed=old_urls-urls
 if removed:
  hashes=','.join(hashlib.sha256(x.encode()).hexdigest() for x in removed)
  api('url_snapshots','PATCH',{'active':False,'last_seen_at':now},{'website_id':f"eq.{site['id']}",'url_hash':f'in.({hashes})'})
 rows=[{'website_id':site['id'],'url':u,'url_hash':hashlib.sha256(u.encode()).hexdigest(),'active':True,'last_seen_at':now} for u in urls]
 for i in range(0,len(rows),500):
  h={**HEAD,'Prefer':'resolution=merge-duplicates'}
  r=requests.post(f'{BASE}/rest/v1/url_snapshots?on_conflict=website_id,url_hash',headers=h,json=rows[i:i+500],timeout=30); r.raise_for_status()
 api('websites','PATCH',{'status':'ok','last_total':len(urls),'last_error':'; '.join(warnings[:3]) or None,'last_scanned_at':now,'robots_hash':rh,'sitemap_url':site.get('sitemap_url') or maps[0]},{'id':f"eq.{site['id']}"})
 api('scan_history','POST',{'website_id':site['id'],'user_id':site['user_id'],'status':'ok','total_urls':len(urls),'added_count':len(added),'removed_count':len(removed),'robots_changed':robots_changed})
 if added or removed or robots_changed: notify(f"🔎 {site['name']}\n总量 {len(urls)}｜新增 {len(added)}｜删除 {len(removed)}"+('\nrobots.txt 已变化' if robots_changed else ''))
 print(f"OK {site['name']}: total={len(urls)} +{len(added)} -{len(removed)}")

def fail(site,e):
 msg=str(e)[:1000]; now=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
 api('websites','PATCH',{'status':'error','last_error':msg,'last_scanned_at':now},{'id':f"eq.{site['id']}"})
 api('scan_history','POST',{'website_id':site['id'],'user_id':site['user_id'],'status':'error','total_urls':site.get('last_total',0),'error':msg})
 notify(f"❌ {site['name']} Sitemap 扫描失败\n{msg}"); print(f"ERROR {site['name']}: {msg}",file=sys.stderr)

if __name__=='__main__':
 if not BASE or not KEY: raise SystemExit('缺少 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY')
 sites=api('websites',params={'select':'*'}) or []
 for site in sites:
  try: scan(site)
  except Exception as e: fail(site,e)
 print(f'扫描完成：{len(sites)} 个网站')
