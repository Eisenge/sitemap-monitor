import hashlib, os, re, sys, time, xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
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
STOP=set('the a an and or for to of in on with from by is are be this that it as at your our you we us can will more new home about into how what why who when where these those their its not all'.split())

class PageParser(HTMLParser):
 def __init__(self): super().__init__(); self.title=[]; self.h1=[]; self.text=[]; self.meta=''; self.stack=[]
 def handle_starttag(self,tag,attrs):
  self.stack.append(tag); a=dict(attrs)
  if tag=='meta' and (a.get('name','').lower()=='description' or a.get('property','').lower()=='og:description'): self.meta=self.meta or a.get('content','')
 def handle_endtag(self,tag):
  if tag in self.stack: self.stack=self.stack[:len(self.stack)-1-self.stack[::-1].index(tag)]
 def handle_data(self,data):
  if any(x in self.stack for x in ('script','style','noscript','svg')): return
  s=' '.join(data.split())
  if not s:return
  if 'title' in self.stack:self.title.append(s)
  if 'h1' in self.stack:self.h1.append(s)
  self.text.append(s)

def extract_keywords(title,h1,meta,text,limit=12):
 weighted=Counter(); corpus=' '.join((title,h1,meta,text[:50000])).lower()
 words=re.findall(r"[a-z][a-z0-9'-]{2,}",corpus)
 clean=[w for w in words if w not in STOP and not w.isdigit()]
 for n in (1,2,3):
  for i in range(len(clean)-n+1):
   term=' '.join(clean[i:i+n]); weighted[term]+=1+(n-1)*0.8
 for source,boost in ((title,5),(h1,4),(meta,2)):
  low=source.lower()
  for term in list(weighted):
   if term in low: weighted[term]+=boost
 for run in re.findall(r'[\u3400-\u9fff]{2,20}',corpus):
  for n in (2,3,4):
   for i in range(len(run)-n+1):weighted[run[i:i+n]]+=1+n*.4
 chosen=[]
 for term,score in weighted.most_common(80):
  if any(term in x['term'] or x['term'] in term for x in chosen):continue
  chosen.append({'term':term,'score':round(score,1)})
  if len(chosen)>=limit:break
 return chosen

def analyze_page(site,url):
 now=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()); row={'website_id':site['id'],'user_id':site['user_id'],'url':url,'url_hash':hashlib.sha256(url.encode()).hexdigest(),'analyzed_at':now}
 try:
  r=get(url); ctype=r.headers.get('content-type','')
  if 'html' not in ctype.lower():raise RuntimeError(f'非 HTML 页面: {ctype}')
  p=PageParser();p.feed(r.text[:1000000]);title=' '.join(p.title)[:500];h1=' | '.join(p.h1[:3])[:1000];meta=p.meta[:1000];body=' '.join(p.text)
  row.update({'title':title,'meta_description':meta,'h1':h1,'language':'zh' if re.search(r'[\u3400-\u9fff]',body) else 'en','keywords':extract_keywords(title,h1,meta,body),'error':None})
 except Exception as e:row.update({'keywords':[],'error':str(e)[:1000]})
 h={**HEAD,'Prefer':'resolution=merge-duplicates'}
 r=requests.post(f'{BASE}/rest/v1/page_insights?on_conflict=website_id,url_hash',headers=h,json=row,timeout=30);r.raise_for_status()
 return row

def analyze_pending(site,active_urls):
 done=api('page_insights',params={'website_id':f"eq.{site['id']}",'select':'url_hash'}) or [];done={x['url_hash'] for x in done};limit=int(os.getenv('MAX_PAGE_ANALYSIS','25'))
 candidates=[u for u in sorted(active_urls) if hashlib.sha256(u.encode()).hexdigest() not in done][:limit]
 rows=[analyze_page(site,u) for u in candidates]
 return rows

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
 insights=analyze_pending(site,urls)
 api('websites','PATCH',{'status':'ok','last_total':len(urls),'last_error':'; '.join(warnings[:3]) or None,'last_scanned_at':now,'robots_hash':rh,'sitemap_url':site.get('sitemap_url') or maps[0]},{'id':f"eq.{site['id']}"})
 api('scan_history','POST',{'website_id':site['id'],'user_id':site['user_id'],'status':'ok','total_urls':len(urls),'added_count':len(added),'removed_count':len(removed),'robots_changed':robots_changed})
 if added or removed or robots_changed:
  terms=[]
  for x in insights:terms.extend(k['term'] for k in x.get('keywords',[])[:5])
  top=', '.join(k for k,_ in Counter(terms).most_common(10))
  notify(f"🔎 {site['name']}\n总量 {len(urls)}｜新增 {len(added)}｜删除 {len(removed)}"+('\nrobots.txt 已变化' if robots_changed else '')+(f'\n新页面关键词：{top}' if top else ''))
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
