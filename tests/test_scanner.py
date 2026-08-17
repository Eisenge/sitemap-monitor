import scanner

def test_nested_sitemap(monkeypatch):
 docs={'https://x.test/sitemap.xml':b'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>https://x.test/a.xml</loc></sitemap></sitemapindex>','https://x.test/a.xml':b'<urlset><url><loc>https://x.test/a</loc></url><url><loc>https://x.test/b</loc></url></urlset>'}
 class Response:
  def __init__(self,content): self.content=content
 monkeypatch.setattr(scanner,'get',lambda url:Response(docs[url]))
 urls,errors=scanner.crawl(['https://x.test/sitemap.xml'])
 assert urls=={'https://x.test/a','https://x.test/b'}
 assert errors==[]

def test_robots_discovery(monkeypatch):
 class Response: text='User-agent: *\nSitemap: https://x.test/one.xml\nSITEMAP: https://x.test/two.xml'
 monkeypatch.setattr(scanner,'get',lambda url:Response())
 _,maps=scanner.discover('https://x.test')
 assert maps==['https://x.test/one.xml','https://x.test/two.xml']
