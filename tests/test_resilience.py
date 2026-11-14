import sys,unittest,tempfile,json
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch,Mock
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import pipeline as p
import ecosystem as e
import watchdog as w
import publication as pub
NOW=datetime(2026,11,14,12,tzinfo=timezone.utc)
SOURCE={'id':'sample','family':'sample','homepage':'https://example.com/','language':'en','section':'israel','feed_urls':['https://example.com/broken','https://example.com/backup']}
def rss(date='Sat, 14 Nov 2026 10:00:00 GMT'):
 return ('<rss><channel><item><title>A current report</title><link>https://example.com/article</link><pubDate>'+date+'</pubDate></item></channel></rss>').encode()
def run(ident=1,state='completed',conclusion='success',hours=1,title='MORIAH publication'):
 return {'id':ident,'status':state,'conclusion':conclusion,'created_at':p.iso(NOW-timedelta(hours=hours)),'updated_at':p.iso(NOW-timedelta(hours=hours)),'display_title':title}
class FeedRecoveryTests(unittest.TestCase):
 def test_failure_switches_to_backup_and_next_poll_prefers_it(self):
  with patch.object(p,'fetch',side_effect=[HTTPError('u',404,'not found',{},None),(rss(),{})]) as fetch:
   items,status=p.poll(SOURCE,NOW)
  self.assertEqual(len(items),1);self.assertEqual(status['state'],'ok');self.assertTrue(status['recovered']);self.assertEqual(status['feed_url'],SOURCE['feed_urls'][1])
  state=p.feed_state_update({},status)
  with patch.object(p,'fetch',return_value=(rss(),{})) as fetch:
   p.poll(SOURCE,NOW,state)
  self.assertEqual(fetch.call_args_list[0].args[0],SOURCE['feed_urls'][1]);self.assertEqual(fetch.call_count,1)
 def test_stale_primary_does_not_hide_fresh_backup(self):
  with patch.object(p,'fetch',side_effect=[(rss('Sun, 01 Nov 2026 10:00:00 GMT'),{}),(rss(),{})]):
   _,status=p.poll(SOURCE,NOW)
  self.assertEqual(status['feed_url'],SOURCE['feed_urls'][1]);self.assertEqual(status['state'],'ok')
 def test_discovers_only_publisher_advertised_feed(self):
  source={**SOURCE,'feed_urls':['https://example.com/broken']}
  html=b'<html><link rel="alternate" type="application/rss+xml" href="/new.xml"><link rel="alternate" type="application/rss+xml" href="https://evil.example/steal"></html>'
  def fetch(url,**kwargs):
   if url.endswith('/broken'):raise HTTPError(url,404,'not found',{},None)
   return (html,{}) if url==source['homepage'] else (rss(),{})
  with patch.object(p,'fetch',side_effect=fetch) as mocked:_,status=p.poll(source,NOW)
  self.assertEqual(status['feed_url'],'https://example.com/new.xml');self.assertEqual(status['recovery'],'discovered');self.assertTrue(all('evil.example' not in x.args[0] for x in mocked.call_args_list))
 def test_discovery_is_rate_limited_and_untrusted_saved_urls_are_ignored(self):
  state={'discovered_at':p.iso(NOW-timedelta(hours=1)),'discovered_urls':['https://evil.example/rss'],'preferred_url':'https://evil.example/rss'}
  with patch.object(p,'fetch',side_effect=HTTPError('u',403,'Forbidden',{},None)) as fetch:
   _,status=p.poll(SOURCE,NOW,state)
  self.assertEqual(fetch.call_count,2);self.assertEqual(status['state'],'unavailable')
 def test_category_discovery_does_not_replace_torah_with_general_news(self):
  parser=p.FeedLinks('https://example.com/',{**SOURCE,'feed_path_pattern':'torah'})
  parser.feed('<link rel="alternate" type="application/rss+xml" href="/rss/news"><link rel="alternate" type="application/rss+xml" href="/rss/torah">')
  self.assertEqual(parser.links,['https://example.com/rss/torah'])
 def test_stale_entries_remain_old_and_failed_sources_do_not_reset_freshness(self):
  item={'published_at':p.iso(NOW-timedelta(hours=1))}
  status={'id':'sample','state':'unavailable'}
  self.assertEqual(p.collection_health([item],[status],NOW)['state'],'degraded')
  self.assertEqual(p.collection_health([item],[{'id':'sample','state':'ok'}],NOW)['state'],'ok')
 def test_external_redirect_is_rejected(self):
  with patch.object(p,'fetch',return_value=(rss(),{'_final_url':'https://evil.example/rss'})):
   _,status=p.poll({**SOURCE,'poll_budget_seconds':1},NOW,{'discovered_at':p.iso(NOW)})
  self.assertEqual(status['state'],'unavailable')
 def test_429_honours_bounded_retry_after(self):
  response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.read.return_value=b'<rss/>';response.url='https://example.com/feed';response.headers={}
  with patch.object(p,'urlopen',side_effect=[HTTPError('u',429,'retry',{'Retry-After':'500'},None),response]),patch.object(p.time,'sleep') as sleep:
   self.assertEqual(p.fetch('https://example.com/feed')[0],b'<rss/>')
  sleep.assert_called_once_with(4)
 def test_total_feed_outage_preserves_last_success_timestamp(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);source={**SOURCE,'id':'sample'};generated=p.iso(NOW-timedelta(hours=4))
   item={'id':'one','title':'A report','titles':{'en':'A report'},'source_id':'sample','family':'sample','section':'israel','source_language':'en','url':'https://example.com/article','published_at':p.iso(NOW-timedelta(hours=5)),'type':'news','translation':{}}
   settings={'launch_date':'2026-10-24','cities':[],'translate':False};features=[{'title':{'he':'דוגמה','en':'Example'},'section':'israel'}]
   for path,value in [('config/settings.json',settings),('config/sources.json',[source]),('config/channels.json',[]),('config/sections.json',[{'id':'israel'}]),('content/features.json',features),('data/latest.json',{'generated_at':generated,'news':[item],'videos':[]}),('data/issues/2026-11-11.json',{'id':'2026-11-11','launch':False,'revision':1,'published_at':generated})]:p.save(root/path,value)
   status={'id':'sample','state':'unavailable','items':0,'checked_at':p.iso(NOW),'error':'offline'}
   with patch.dict(p.os.environ,{'GITHUB_STEP_SUMMARY':''}),patch.object(p,'ROOT',root),patch.object(sys,'argv',['pipeline.py','--no-translate','--now',p.iso(NOW)]),patch.object(p,'poll',return_value=([],status)),patch.object(p,'calendar',return_value={}),patch.object(p,'learning_calendar',return_value={}):p.main()
   self.assertEqual(p.load(root/'data/latest.json')['generated_at'],generated);self.assertEqual(p.load(root/'data/health.json')['state'],'degraded')
class OptionalStudyTests(unittest.TestCase):
 def test_incomplete_external_qa_is_rejected_before_replacing_cache(self):
  with self.assertRaises(ValueError):e.validate_section('qa',{'cards':[]})
 def test_rolling_weeks_keep_known_history_and_replace_changed_readings(self):
  first={'target_shabbat':'2026-10-24','israel':{'he':'לך לך'},'diaspora':{'he':'לך לך'}};changed={**first,'israel':{'he':'תיקון'}}
  result=e.merge_weeks([first],[changed,{'target_shabbat':'invalid'}]);self.assertEqual(len(result),1);self.assertEqual(result[0]['israel']['he'],'תיקון')
class WatchdogTests(unittest.TestCase):
 def state(self):return {'generated_at':p.iso(NOW-timedelta(hours=1)),'news':[{'published_at':p.iso(NOW-timedelta(hours=2))}]},{'state':'ok'}
 def test_healthy_publication_is_not_restarted(self):
  data,health=self.state();self.assertEqual(w.decision([run()],data,health,NOW)['action'],'healthy')
 def test_failure_dispatches_fresh_main_in_recovery_mode(self):
  data,health=self.state();plan=w.decision([run(conclusion='failure')],data,health,NOW);api=Mock();w.execute(api,plan)
  api.request.assert_called_once_with('actions/workflows/newspaper.yml/dispatches',{'ref':'main','inputs':{'recovery':True}})
 def test_stale_public_data_is_detected_even_after_successful_workflow(self):
  data,health=self.state();data['generated_at']=p.iso(NOW-timedelta(hours=12));self.assertEqual(w.decision([run()],data,health,NOW)['action'],'recover')
 def test_active_publish_and_propagation_grace_prevent_duplicate_runs(self):
  data,health=self.state()
  for r in [run(state='in_progress',hours=.1),run(hours=.05)]:self.assertEqual(w.decision([r],data,health,NOW)['action'],'wait')
 def test_three_recoveries_in_six_hours_stop_a_failure_loop(self):
  data,health=self.state();runs=[run(i,conclusion='failure',title='MORIAH recovery',hours=i) for i in [1,2,3]]
  self.assertEqual(w.decision(runs,data,health,NOW)['action'],'limited')
 def test_stuck_job_is_cancelled_before_dispatch(self):
  data,health=self.state();plan=w.decision([run(state='in_progress',hours=1)],data,health,NOW);api=Mock();w.execute(api,plan)
  self.assertEqual(api.request.call_args_list[0].args,('actions/runs/1/cancel',{}));self.assertEqual(api.request.call_args_list[1].args[0],'actions/workflows/newspaper.yml/dispatches')
 def test_healthy_state_is_not_reported_as_limited_after_three_recoveries(self):
  data,health=self.state();runs=[run(i,title='MORIAH recovery',hours=i) for i in [1,2,3]]
  self.assertEqual(w.decision(runs,data,health,NOW)['action'],'healthy')
 def test_stalled_recovery_also_respects_dispatch_budget(self):
  data,health=self.state();runs=[run(0,state='in_progress',hours=1)]+[run(i,title='MORIAH recovery',hours=i) for i in [2,3,4]]
  plan=w.decision(runs,data,health,NOW);self.assertEqual(plan['action'],'cancel_only');api=Mock();w.execute(api,plan);api.request.assert_called_once_with('actions/runs/0/cancel',{})
 def test_marker_verification_retries_an_old_cdn_response(self):
  data=p.load(p.ROOT/'data/latest.json');old={'run_id':'old'};correct={'run_id':'new','run_attempt':p.os.getenv('GITHUB_RUN_ATTEMPT','1'),'generated_at':data['generated_at']}
  with patch.object(pub,'public_json',side_effect=[old,correct,data]),patch.object(pub.time,'sleep'):
   self.assertEqual(pub.verify('new',attempts=2),correct)
if __name__=='__main__':unittest.main()
