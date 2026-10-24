import sys,unittest,json,tempfile
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pipeline import *

NOW=datetime(2026,10,24,12,tzinfo=timezone.utc)
SOURCE={'id':'test','family':'test','homepage':'https://example.com/','language':'en','section':'israel'}
class FeedTests(unittest.TestCase):
 def rss(self,items):return ('<rss><channel>'+items+'</channel></rss>').encode()
 def item(self,title='A headline',url='https://example.com/story',date='Sat, 24 Oct 2026 10:00:00 GMT'):
  return f'<item><title>{html.escape(title)}</title><link>{html.escape(url)}</link><pubDate>{date}</pubDate></item>'
 def test_rss_sanitizes_and_canonicalizes(self):
  x=parse_feed(self.rss(self.item('<b>Important</b> & real','https://example.com/story?utm_source=x&amp;a=2')),SOURCE,NOW)[0]
  self.assertEqual(x['title'],'Important & real');self.assertNotIn('utm_',x['url'])
 def test_external_link_rejected(self):self.assertEqual(parse_feed(self.rss(self.item(url='https://evil.example/story')),SOURCE,NOW),[])
 def test_script_url_rejected(self):self.assertEqual(parse_feed(self.rss(self.item(url='javascript:alert(1)')),SOURCE,NOW),[])
 def test_future_items_rejected(self):self.assertEqual(parse_feed(self.rss(self.item(date='Sun, 25 Oct 2026 10:00:00 GMT')),SOURCE,NOW),[])
 def test_undated_not_falsely_dated(self):self.assertIsNone(parse_feed(self.rss(self.item(date='not a date')),SOURCE,NOW)[0]['published_at'])
 def test_dtd_rejected(self):
  with self.assertRaises(ValueError):parse_feed(b'<!DOCTYPE rss [<!ENTITY a "hello">]><rss/>',SOURCE,NOW)
 def test_atom_youtube(self):
  s={**SOURCE,'homepage':'https://www.youtube.com/','type':'video','allowed_domains':['youtube.com']}
  b=b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015"><entry><title>A video</title><link href="https://www.youtube.com/watch?v=abcdefghijk"/><published>2026-10-24T10:00:00Z</published><yt:videoId>abcdefghijk</yt:videoId></entry></feed>'
  x=parse_feed(b,s,NOW)[0];self.assertEqual(x['type'],'video');self.assertEqual(x['video_id'],'abcdefghijk')
 def test_hebrew_source_detected(self):self.assertEqual(parse_feed(self.rss(self.item('חדשות מהעיר ירושלים')),SOURCE,NOW)[0]['source_language'],'he')
 def test_xml_wrong_encoding_fallback(self):
  b=b'<?xml version="1.0" encoding="UTF-16"?>'+self.rss(self.item())
  self.assertEqual(len(parse_feed(b,SOURCE,NOW)),1)
 def test_date_timezone_normalized(self):self.assertEqual(iso(parse_date('2026-10-24T13:00:00+03:00')),'2026-10-24T10:00:00Z')
 def test_url_security(self):
  for s in ['http://x.com/','https://user:password@x.com/','https://x.com:8080/','data:text/plain,hey']:self.assertFalse(safe_url(s))
 def test_tracking_deduplication(self):self.assertEqual(canonical('https://example.com/s?utm_medium=x'),canonical('https://example.com/s?fbclid=y'))

class EditionTests(unittest.TestCase):
 def test_launch_not_backdated(self):self.assertEqual(due_issue(NOW,'2026-10-24'),('2026-10-24-launch',True))
 def test_wednesday_dst(self):
  self.assertEqual(due_issue(parse_date('2026-10-28T15:59:00Z'),'2026-10-24'),('2026-10-24-launch',True))
  self.assertEqual(due_issue(parse_date('2026-10-28T16:00:00Z'),'2026-10-24'),('2026-10-28',False))
 def test_late_run_catches_up(self):self.assertEqual(due_issue(parse_date('2026-10-29T12:00:00Z'),'2026-10-24'),('2026-10-28',False))
 def test_family_diversity(self):
  x=diversify([{'family':'a','id':i} for i in range(8)]+[{'family':'b','id':9}],5,2)
  self.assertEqual(len(x),3)
 def test_number_translation_guard(self):
  self.assertFalse(valid_translation('12 people','שלושה אנשים','he'));self.assertTrue(valid_translation('12 people','12 אנשים','he'))
 def test_offline_enrichment_no_fake_translation(self):
  x=[{'title':'שלום מירושלים','source_language':'he'}];enrich(x,{},0,False)
  self.assertEqual(x[0]['titles'],{'he':'שלום מירושלים'});self.assertEqual(x[0]['translation'],{})
 def test_translation_cache_and_provenance(self):
  class Fake:
   def translate_many(self,texts,src,dst):return ['Hello Jerusalem']*len(texts)
  x=[{'title':'שלום ירושלים','source_language':'he'}];cache={};self.assertEqual(enrich(x,cache,1,translator=Fake()),[])
  self.assertEqual(x[0]['titles']['en'],'Hello Jerusalem');self.assertEqual(x[0]['translation']['en'],'machine');self.assertEqual(len(cache),1)
 def test_enrichment_failure_isolated(self):
  class Broken:
   def translate_many(self,*args):raise RuntimeError('offline')
  x=[{'title':'שלום ירושלים','source_language':'he'}];errs=enrich(x,{},1,translator=Broken());self.assertEqual(len(errs),1);self.assertNotIn('en',x[0]['titles'])
 def test_immutable_snapshot_contains_revision(self):
  p=ROOT/'data/issues';files=list(p.glob('*.json')) if p.exists() else []
  for f in files:
   d=load(f);self.assertEqual(d['revision'],1);self.assertTrue(d['automated']);self.assertTrue(d['published_at'])
 def test_sections_complete_unique(self):
  s=load(ROOT/'config/sections.json');self.assertEqual(len(s),24);self.assertEqual(len({x['id'] for x in s}),24)
 def test_channel_ids_not_handles(self):
  for c in load(ROOT/'config/channels.json'):
   self.assertRegex(c['channel_id'],r'^UC[\w-]{22}$');self.assertTrue(c['identity_checked_at'])
 def test_all_sections_have_bilingual_learning_material(self):
  articles=load(ROOT/'content/features.json');sections={s['id'] for s in load(ROOT/'config/sections.json')}
  self.assertEqual({a['section'] for a in articles},sections)
  self.assertTrue(all(a['body']['he'] and a['body']['en'] for a in articles))
 def test_weekly_features_rotate_without_duplicates(self):
  articles=load(ROOT/'content/features.json');a=issue_features(articles,'2026-10-28',False);b=issue_features(articles,'2026-11-04',False)
  self.assertEqual(len(a),10);self.assertEqual(len({x['id'] for x in a}),10);self.assertNotEqual([x['id'] for x in a],[x['id'] for x in b])
 def test_snapshot_valid(self):
  d=load(ROOT/'data/latest.json');self.assertTrue(validate(d))

if __name__=='__main__':unittest.main()
