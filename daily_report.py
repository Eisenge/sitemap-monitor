import os, smtplib, time
from collections import Counter, defaultdict
from email.message import EmailMessage
import requests

BASE=os.environ.get('SUPABASE_URL','').rstrip('/');KEY=os.environ.get('SUPABASE_SERVICE_ROLE_KEY','')
HEAD={'apikey':KEY,'Content-Type':'application/json'}
if KEY.count('.')==2:HEAD['Authorization']=f'Bearer {KEY}'
def api(path,params=None):
 r=requests.get(f'{BASE}/rest/v1/{path}',headers=HEAD,params=params,timeout=30);r.raise_for_status();return r.json()
def build_report(sites,history,insights):
 names={x['id']:x['name'] for x in sites};changes=defaultdict(lambda:[0,0,0]);errors=[]
 for row in history:
  changes[row['website_id']][0]+=row.get('added_count',0);changes[row['website_id']][1]+=row.get('removed_count',0);changes[row['website_id']][2]=row.get('total_urls',0)
  if row.get('status')=='error':errors.append(f"{names.get(row['website_id'],'未知网站')}: {row.get('error','扫描失败')}")
 terms=Counter();new_pages=[]
 for row in insights:
  if not row.get('error'):new_pages.append(row);terms.update(k['term'] for k in row.get('keywords',[])[:8])
 lines=['📊 Sitemap Monitor 日报',time.strftime('%Y-%m-%d',time.localtime()),'',f"监控网站：{len(sites)}｜分析页面：{len(new_pages)}｜异常：{len(errors)}"]
 changed=False
 for site in sites:
  add,remove,total=changes[site['id']]
  if add or remove:changed=True;lines.append(f"• {site['name']}：总量 {total}，新增 {add}，删除 {remove}")
 if not changed:lines.append('• 最近 24 小时 Sitemap 无 URL 变化')
 if terms:lines.extend(['','🔥 新页面高频关键词',', '.join(x for x,_ in terms.most_common(20))])
 if new_pages:
  lines.extend(['','🆕 最近分析页面'])
  for row in new_pages[:10]:lines.append(f"• {names.get(row['website_id'],'')}｜{row.get('title') or row['url']}")
 if errors:lines.extend(['','⚠️ 异常',*('• '+x for x in errors[:10])])
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
 since=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(time.time()-86400));sites=api('websites',{'select':'id,name,status,last_total','order':'name'});history=api('scan_history',{'select':'*','scanned_at':f'gte.{since}','order':'scanned_at.asc'});insights=api('page_insights',{'select':'*','analyzed_at':f'gte.{since}','order':'analyzed_at.desc'});message=build_report(sites,history,insights);token=os.getenv('TELEGRAM_BOT_TOKEN');chat=os.getenv('TELEGRAM_CHAT_ID');sent=[]
 if token and chat:
  r=requests.post(f'https://api.telegram.org/bot{token}/sendMessage',json={'chat_id':chat,'text':message,'disable_web_page_preview':True},timeout=20);r.raise_for_status();sent.append('Telegram')
 if send_email(message):sent.append('邮箱')
 if not sent:raise SystemExit('未配置 Telegram 或邮箱发送密钥')
 print('日报发送成功：'+', '.join(sent))
if __name__=='__main__':main()
