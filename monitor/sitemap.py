import json
import requests

def check(url):
    try:
        r=requests.get(url,timeout=10)
        return r.status_code
    except:
        return 0

with open('../data/websites.json') as f:
    sites=json.load(f)

for site in sites:
    print(site['name'], check(site['url']))
