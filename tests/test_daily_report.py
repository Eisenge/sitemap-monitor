from daily_report import build_report
def test_report_contains_changes_and_keywords():
 text=build_report([{'id':'1','name':'Zoomex'}],[{'website_id':'1','added_count':3,'removed_count':1,'total_urls':100,'status':'ok'}],[{'website_id':'1','url':'https://x/new','title':'AI Trading','keywords':[{'term':'ai trading'},{'term':'bitcoin'}]}])
 assert '新增 3' in text and '删除 1' in text and 'ai trading' in text and 'AI Trading' in text
