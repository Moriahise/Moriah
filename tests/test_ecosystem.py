import sys,unittest,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ecosystem
class IntegrationTests(unittest.TestCase):
 def test_external_audio_cannot_escape_collection(self):
  base='https://moriahise.github.io/Niggun/'
  self.assertIsNone(ecosystem.rel_url(base,'https://evil.example/track.mp3'))
  self.assertIsNone(ecosystem.rel_url(base,'../other/track.mp3'))
  self.assertIsNone(ecosystem.rel_url(base,'javascript:alert(1)'))
  self.assertIn('%D7',ecosystem.rel_url(base,'שיר.mp3'))
 def test_youtube_is_parsed_without_running_scripts(self):
  self.assertEqual(ecosystem.youtube_id('https://youtu.be/kMgXtS54-iU'),'kMgXtS54-iU')
  self.assertEqual(ecosystem.youtube_id('https://www.youtube.com/watch?v=kMgXtS54-iU'),'kMgXtS54-iU')
  self.assertIsNone(ecosystem.youtube_id('https://example.com/watch?v=kMgXtS54-iU'))
 def test_playlists_only_contain_existing_published_tracks(self):
  seed={'entries':[{'id':'one','titleHe':'ניגון','page':'song.html','youtube':'https://youtu.be/kMgXtS54-iU','category':'Shabbat'}], 'playlists':[{'id':'p','name':'Collection','items':['one','missing']}]}
  with patch.object(ecosystem,'text',return_value='<script id="seed" type="application/json">'+json.dumps(seed)+'</script>'):
   result=ecosystem.music_seed({'id':'test','url':'https://moriahise.github.io/Niggun/'})
  self.assertEqual(result['playlists'][0]['items'],['one']);self.assertEqual(result['series'][0]['items'],['one'])
 def test_bilingual_text_is_read_from_explicit_language_spans(self):
  d=ecosystem.Document('<h3><span lang="en">English</span><span lang="he">עברית</span></h3>')
  self.assertEqual(ecosystem.bilingual(d.root.find('h3')[0]),{'en':'English','he':'עברית'})
if __name__=='__main__':unittest.main()
