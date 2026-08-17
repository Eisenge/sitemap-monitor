from daily_report import build_report
def test_report_contains_changes_and_keywords():
 text=build_report([{'id':'g1','name':'加密货币'},{'id':'g2','name':'小游戏'}],[{'id':'1','name':'Zoomex','group_id':'g1'},{'id':'2','name':'Poki','group_id':'g2'}],[{'website_id':'1','added_count':3,'removed_count':1,'total_urls':100,'status':'ok'}],[{'website_id':'1','url':'https://x/new','title':'AI Trading','keywords':[{'term':'ai trading'},{'term':'bitcoin'}]}])
 assert '【加密货币】' in text and '新增 3' in text and '删除 1' in text
 assert 'ai trading' in text and 'AI Trading' in text
 assert '【小游戏】' in text and '最近 24 小时无 URL 变化' in text
