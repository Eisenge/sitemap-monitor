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

def test_page_parser_and_keywords():
 parser=scanner.PageParser()
 parser.feed('<html><head><title>Bitcoin Trading Guide</title><meta name="description" content="Learn crypto trading strategies"></head><body><h1>Bitcoin Trading</h1><script>ignore noise</script><p>Bitcoin trading strategies for beginners and crypto traders.</p></body></html>')
 title=' '.join(parser.title);h1=' '.join(parser.h1);body=' '.join(parser.text)
 terms=[x['term'] for x in scanner.extract_keywords(title,h1,parser.meta,body)]
 assert title=='Bitcoin Trading Guide'
 assert 'Bitcoin Trading'==h1
 assert any('bitcoin' in x for x in terms)
 assert 'ignore noise' not in body
