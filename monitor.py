import json
import requests
import os
import hashlib
import xml.etree.ElementTree as ET

CONFIG="config.json"
DATA="data.json"

def fetch(url):
    r=requests.get(url,timeout=30)
    r.raise_for_status()
    return r.text

def parse_urls(xml):
    root=ET.fromstring(xml)
    urls=[]
    for item in root.iter():
        if item.tag.endswith("loc") and item.text:
            urls.append(item.text.strip())
    return sorted(list(set(urls)))

def telegram(msg):
    token=os.getenv("TELEGRAM_TOKEN")
    chat=os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id":chat,"text":msg}
    )

with open(CONFIG) as f:
    config=json.load(f)

try:
    with open(DATA) as f:
        history=json.load(f)
except:
    history={}

changed=False

for site in config["websites"]:
    name=site["name"]
    sitemap=site["sitemap"]

    xml=fetch(sitemap)
    urls=parse_urls(xml)

    old=set(history.get(name, []))
    new=set(urls)

    added=new-old
    removed=old-new

    if added or removed:
        changed=True
        msg=f"🚨 Sitemap Changed\\n\\n{name}\\n"
        if added:
            msg += "\\nNew URLs:\\n" + "\\n".join(list(added)[:20])
        if removed:
            msg += "\\n\\nRemoved URLs:\\n" + "\\n".join(list(removed)[:20])
        telegram(msg)

    history[name]=urls

with open(DATA,"w") as f:
    json.dump(history,f,indent=2)

print("Monitor finished")
