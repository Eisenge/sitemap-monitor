import os, smtplib, time
from collections import Counter, defaultdict
from email.message import EmailMessage
import requests

BASE=os.environ.get('SUPABASE_URL','').rstrip('/');KEY=os.environ.get('SUPABASE_SERVICE_ROLE_KEY','')
HEAD={'apikey':KEY,'Content-Type':'application/json'}
if KEY.count('.')==2:HEAD['Authorization']=f'Bearer {KEY}'
def api(path,params=None):
 r=requests.get(f'{BASE}/rest/v1/{path}',headers=HEAD,params=params,timeout=30);r.raise_for_status();return r.json()
def build_report(groups,sites,history,insights):
 names={x['id']:x['name'] for x in sites};changes=defaultdict(lambda:[0,0,0]);errors=defaultdict(list)
 for row in history:
  changes[row['website_id']][0]+=row.get('added_count',0);changes[row['website_id']][1]+=row.get('removed_count',0);changes[row['website_id']][2]=row.get('total_urls',0)
  if row.get('status')=='error':errors[row['website_id']].append(row.get('error','扫描失败'))
 new_pages=[]
 for row in insights:
  if not row.get('error'):new_pages.append(row)
 total_added=sum(x[0] for x in changes.values());total_removed=sum(x[1] for x in changes.values())
 all_terms=Counter(k['term'] for x in new_pages for k in x.get('keywords',[])[:8])
 active_sites=sum(1 for s in sites if changes[s['id']][0] or changes[s['id']][1])
 lines=['📊 Sitemap Monitor 分组日报',time.strftime('%Y-%m-%d',time.localtime()),'',
  '【今日总结】',f"监控 {len(sites)} 个网站｜发生变化 {active_sites} 个｜新增 {total_added}｜删除 {total_removed}｜新页面分析 {len(new_pages)}｜异常 {len(errors)}"]
 if all_terms:lines.append('今日主要关键词：'+', '.join(x for x,_ in all_terms.most_common(12)))
 sections=[(g['id'],g['name']) for g in groups]
 if any(not s.get('group_id') for s in sites):sections.append((None,'未分组'))
 for group_id,group_name in sections:
  group_sites=[s for s in sites if s.get('group_id')==group_id];site_ids={s['id'] for s in group_sites}
  added=sum(changes[x][0] for x in site_ids);removed=sum(changes[x][1] for x in site_ids);group_errors=sum(1 for x in site_ids if x in errors)
  group_pages=[x for x in new_pages if x['website_id'] in site_ids];terms=Counter(k['term'] for x in group_pages for k in x.get('keywords',[])[:8])
  lines.extend(['',f"【{group_name}】{len(group_sites)} 个网站｜新增 {added}｜删除 {removed}｜异常 {group_errors}"])
  changed_sites=[s for s in group_sites if changes[s['id']][0] or changes[s['id']][1]]
  if changed_sites:
   for site in changed_sites:lines.append(f"• {site['name']}：总量 {changes[site['id']][2]}，新增 {changes[site['id']][0]}，删除 {changes[site['id']][1]}")
  else:lines.append('• 最近 24 小时无 URL 变化')
  if terms:lines.append('TDK/H1 综合关键词：'+', '.join(x for x,_ in terms.most_common(10)))
  for row in group_pages[:3]:
   lines.append(f"新页面：{names.get(row['website_id'],'')}｜{row.get('title') or row['url']}")
   if row.get('h1'):lines.append(f"  H1：{row['h1'][:160]}")
  for site in group_sites:
   if site['id'] in errors:lines.append(f"⚠️ {site['name']}：{errors[site['id']][-1]}")
 lines.extend(['','【分析】'])
 if total_added or total_removed:
  direction='扩张' if total_added>total_removed else '收缩' if total_removed>total_added else '调整'
  lines.append(f"• 竞品内容整体呈{direction}：新增 {total_added}，删除 {total_removed}。")
 else:lines.append('• 最近 24 小时 Sitemap 稳定，未发现新增或删除页面。')
 if all_terms:
  hot=', '.join(x for x,_ in all_terms.most_common(5));lines.append(f"• 新页面主题集中在：{hot}。这些词值得优先核对搜索意图和现有内容覆盖。")
 if errors:lines.append(f"• {len(errors)} 个网站扫描异常，可能造成变化漏报，应优先排查。")
 lines.extend(['','【建议】'])
 if all_terms:lines.append('1. 从今日高频词中选择 3–5 个与业务最相关的词，检查竞品页面结构、标题和 H1，再决定是否立项。')
 else:lines.append('1. 今日没有新关键词，继续观察，不建议为了更新而盲目创建内容。')
 if total_added:lines.append('2. 优先查看新增页面对应的搜索意图，区分产品页、工具页和资讯页，复制有效选题而不是复制文案。')
 else:lines.append('2. 复查最近一周累计趋势，避免仅凭单日无变化下结论。')
 if errors:lines.append('3. 修复异常站点后重新扫描，避免日报建立在不完整数据上。')
 else:lines.append('3. 对连续多日出现的关键词建立选题池，再结合趋势和实际竞争度安排优先级。')
 return '\n'.join(lines)[:4000]
def send_email(message):
 host=os.getenv('SMTP_HOST');username=os.getenv('SMTP_USERNAME');password=os.getenv('SMTP_PASSWORD');recipient=os.getenv('REPORT_EMAIL_TO')
 if not all((host,username,password,recipient)):return False
 port=int(os.getenv('SMTP_PORT','465'));mail=EmailMessage();mail['Subject']=f"Sitemap Monitor 日报 {time.strftime('%Y-%m-%d')}";mail['From']=os.getenv('REPORT_EMAIL_FROM',username);mail['To']=recipient;mail.set_content(message)
 if port==465:
  with smtplib.SMTP_SSL(host,port,timeout=30) as smtp:smtp.login(username,password);smtp.send_message(mail)
 else:
  with smtplib.SMTP(host,port,timeout=30) as smtp:smtp.starttls();smtp.login(username,password);smtp.send_message(mail)
 return True
def main():
 if not BASE or not KEY:raise SystemExit('缺少 Supabase 配置')
 since=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(time.time()-86400));groups=api('groups',{'select':'id,name','order':'name'});sites=api('websites',{'select':'id,name,group_id,status,last_total','order':'name'});history=api('scan_history',{'select':'*','scanned_at':f'gte.{since}','order':'scanned_at.asc'});insights=api('page_insights',{'select':'*','analyzed_at':f'gte.{since}','order':'analyzed_at.desc'});message=build_report(groups,sites,history,insights);token=os.getenv('TELEGRAM_BOT_TOKEN');chat=os.getenv('TELEGRAM_CHAT_ID');sent=[]
 if token and chat:
  r=requests.post(f'https://api.telegram.org/bot{token}/sendMessage',json={'chat_id':chat,'text':message,'disable_web_page_preview':True},timeout=20);r.raise_for_status();sent.append('Telegram')
 if send_email(message):sent.append('邮箱')
 if not sent:raise SystemExit('未配置 Telegram 或邮箱发送密钥')
 print('日报发送成功：'+', '.join(sent))
if __name__=='__main__':main()
