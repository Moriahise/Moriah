#!/usr/bin/env python3
"""Read the owner's published study catalogues, music seed and Q&A release.
No migrations, edits or large corpus downloads from the upstream projects.
"""
from __future__ import annotations
import concurrent.futures,hashlib,json,re,math
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit,quote
from zoneinfo import ZoneInfo
from pipeline import ROOT,load,save,fetch,iso,plain,safe_url

class Element:
 def __init__(self,tag='',attrs=None):self.tag=tag;self.attrs=attrs or {};self.children=[]
 def text(self):return ' '.join(x.text() if isinstance(x,Element) else x for x in self.children).strip()
 def find(self,tag=None,cls=None):
  result=[]
  for child in self.children:
   if isinstance(child,Element):
    if (tag is None or child.tag==tag) and (not cls or cls in child.attrs.get('class','').split()):result.append(child)
    result+=child.find(tag,cls)
  return result
 def language(self,lang):return ' '.join(n.text() for n in self.find() if n.attrs.get('lang')==lang)
class Document(HTMLParser):
 VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
 def __init__(self,s):super().__init__();self.root=Element();self.stack=[self.root];self.feed(s)
 def handle_starttag(self,t,a):
  n=Element(t,dict(a));self.stack[-1].children.append(n)
  if t not in self.VOID:self.stack.append(n)
 def handle_endtag(self,t):
  for i in range(len(self.stack)-1,0,-1):
   if self.stack[i].tag==t:self.stack=self.stack[:i];break
 def handle_data(self,s):self.stack[-1].children.append(s)

def text(url):return fetch(url)[0].decode('utf-8-sig')
def data(url):return json.loads(fetch(url)[0])
def rel_url(base,path):
 if not path or str(path).startswith(('blob:','data:')):return None
 u=urljoin(base,quote(path,safe='/:%?=&-_.~'))
 b=urlsplit(base);p=urlsplit(u)
 return u if safe_url(u) and p.hostname==b.hostname and p.path.startswith(b.path) else None

def catalogue(base):
 c=data(base+'data/catalogue.json')
 return [dict(e,url=base+'shiur/'+quote(e['id'],safe='-')+'/') for e in c.get('editions',[]) if re.fullmatch(r'[a-zA-Z0-9_-]+',e.get('id',''))]

def bilingual(n):
 return {l:plain(n.language(l),300) for l in ('en','he')}

def music_collections(base):
 d=Document(text(base+'index.html'));result=[]
 for a in d.root.find('a','music-card'):
  url=a.attrs.get('href','')
  if not safe_url(url) or urlsplit(url).hostname!='moriahise.github.io':continue
  h=a.find('h3');p=a.find('p')
  if h:result.append({'id':urlsplit(url).path.strip('/'),'url':url,'title':bilingual(h[0]),'description':bilingual(p[0]) if p else {}})
 return result

def youtube_id(value):
 try:
  p=urlsplit(str(value or ''))
  if p.hostname in ('youtu.be','www.youtu.be'):v=p.path.strip('/')
  elif p.hostname in ('youtube.com','www.youtube.com'):
   from urllib.parse import parse_qs
   v=parse_qs(p.query).get('v',[''])[0] if p.path=='/watch' else p.path.split('/')[-1]
  else:return None
  return v if re.fullmatch(r'[A-Za-z0-9_-]{11}',v) else None
 except Exception:return None

def music_seed(collection):
 html=text(collection['url']);doc=Document(html)
 seeds=[x for x in doc.root.find('script') if x.attrs.get('id')=='seed' and x.attrs.get('type')=='application/json']
 if not seeds:return dict(collection,tracks=[],playlists=[],series=[])
 seed=json.loads(seeds[0].text());tracks=[]
 for e in seed.get('entries',[]):
  if not e.get('id'):continue
  y=youtube_id(e.get('youtube'))
  audio=rel_url(collection['url'],e.get('audio'));page=rel_url(collection['url'],e.get('page'))
  if not(y or audio or page):continue
  h=plain(e.get('titleHe') or e.get('title'),240)
  tracks.append({'id':str(e['id']),'title':{'en':plain(e.get('titleEn') or e.get('title_en') or h,240),'he':h},'source_title':plain(e.get('title'),240),'category':plain(e.get('category'),160),'maqam':plain(e.get('maqam'),90),'sig':plain(e.get('sig'),40),'page_url':page or collection['url'],'audio_url':audio,'youtube_id':y})
 valid={x['id'] for x in tracks};playlists=[]
 for p in seed.get('playlists',[]):
  ids=[str(i) for i in p.get('items',[]) if str(i) in valid]
  if ids:playlists.append({'id':str(p['id']),'title':{'he':plain(p.get('name'),200),'en':plain(p.get('name'),200)},'items':ids})
 groups={}
 for t in tracks:
  if t['category']:groups.setdefault(t['category'],[]).append(t['id'])
 return dict(collection,tracks=tracks,playlists=playlists,series=[{'id':hashlib.sha256(k.encode()).hexdigest()[:12],'title':k,'items':ids} for k,ids in groups.items()])

def haftarot(base):
 d=Document(text(base+'haftarot/'));out=[];seen=set()
 for a in d.root.find('a'):
  href=a.attrs.get('href','');url=urljoin(base+'haftarot/',href)
  if not url.startswith(base+'haftarot/haftarah-') or not url.endswith('/'):continue
  slug=url.rstrip('/').split('/')[-1]
  if slug in seen:continue
  seen.add(slug);title=bilingual(a)
  out.append({'id':slug,'url':url,'title':title})
 return out

def study_preview(base,editions):
 today=datetime.now(ZoneInfo('Asia/Jerusalem')).date().isoformat()
 e=next(iter(sorted([e for e in editions if e.get('target_shabbat','9999')<=today],key=lambda e:e['target_shabbat'],reverse=True)),None)
 if not e:return {}
 d=Document(text(e['url']));parts={}
 for lang in ('en','he'):
  choices=[]
  for n in d.root.find():
   if n.attrs.get('lang')==lang and n.tag!='html':
    for p in ([n] if n.tag in ('span','p') else n.find('p')):
     s=plain(p.text(),420)
     if len(s)>90 and not any(w in s.lower() for w in ['copyright','all rights','cookie']):choices.append(s)
  if choices:parts[lang]=choices[0]
 return {'id':e['id'],'text':parts,'url':e['url']}

def qa_cards(base,limit=9,day=None):
 m=data(base+'catalog/manifest.json')
 if not re.fullmatch(r'releases/v1-[a-f0-9]{24}/',m.get('data_base','')):raise ValueError('Invalid public release')
 prefix=base+m['data_base'];page_size=m['page_size'];fac=m['facets']
 requested={'answered':fac['answer_status']['answered']['file'],'qa':fac['kind']['qa']['file'],'en':fac['language']['en']['file'],'he':fac['language']['he']['file']}
 def get_facet(pair):
  k,path=pair
  if not re.fullmatch(r'catalog/facets/[a-z_]+/[a-f0-9]+\.json',path):raise ValueError('Invalid facet path')
  a=data(prefix+path)
  if not isinstance(a,list):raise ValueError('Invalid facet format')
  return k,set(a)
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:sets=dict(ex.map(get_facet,requested.items()))
 ordinal=day or datetime.now(ZoneInfo('Asia/Jerusalem')).date().toordinal();chosen=[]
 for lang in ('en','he'):
  eligible=sorted(sets['answered']&sets['qa']&sets[lang]);start=(ordinal*limit)%max(1,len(eligible))
  chosen.extend(eligible[(start+i*max(1,len(eligible)//limit))%len(eligible)] for i in range(min(limit,len(eligible))))
 pages=sorted({n//page_size for n in chosen})
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:values=list(ex.map(lambda n:data(prefix+f'catalog/pages/{n:05}.json'),pages))
 records={x['n']:x for page in values for x in page};cards=[]
 def detail(n):
  q=records.get(n)
  if not q or q.get('answers',0)<1:return None
  ident=q['id'];shard=hashlib.sha256(ident.encode()).hexdigest()[:2];locator=data(prefix+'catalog/locator/'+shard+'.json');ref=locator.get(ident)
  if not ref or not re.fullmatch(r'content/[a-f0-9]{2}/[a-f0-9]{64}\.json',ref.get('file','')):return None
  d=data(prefix+ref['file']);answers=d.get('answers',[])
  if not answers:return None
  a=next((a for a in answers if a.get('is_accepted')),answers[0]);license=a.get('license') or d.get('license');license_text=license.get('name','') if isinstance(license,dict) else str(license or '')
  author=a.get('author') or d.get('author') or {}
  author_name=author.get('display_name') or author.get('name') if isinstance(author,dict) else str(author)
  answer=plain(a.get('text') or a.get('body') or a.get('html') or a.get('body_html') or a.get('answer_html'),250) if ('CC BY' in license_text.upper() or d.get('provider')=='local') else ''
  return {'id':ident,'title':plain(q.get('title'),300),'titles':{'en':q.get('title_en',''),'he':q.get('title_he','')},'language':q.get('language','he'),'question':plain(q.get('excerpt'),200),'answer':answer,'answer_count':len(answers),'provider':d.get('provider') or q.get('provider'),'category':q.get('category'),'needs_review':q.get('needs_review',False),'url':base+'qa.html?id='+quote(ident,safe=''),'source_url':d.get('url') or q.get('url'),'author':plain(author_name,100),'author_url':a.get('author_url') or d.get('author_url'),'license':license_text,'snapshot':m['release']}
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
  for f in [ex.submit(detail,n) for n in chosen]:
   try:
    q=f.result()
    if q:cards.append(q)
   except Exception:continue
 return {'release':m['release'],'total':m['total'],'cards':cards}

def collect():
 cfg=load(ROOT/'config/ecosystem.json');old=load(ROOT/'data/ecosystem.json',{});now=datetime.now(timezone.utc)
 result={**old,'schema':1,'checked_at':iso(now),'links':cfg,'status':{}}
 tasks={'shiurim':lambda:{'editions':catalogue(cfg['shiurim']),'weeks':data(cfg['shiurim']+'data/calendar.json')['weeks'],'haftarot':haftarot(cfg['shiurim'])},'zohar':lambda:{'editions':catalogue(cfg['zohar']),'weeks':data(cfg['zohar']+'data/calendar.json')['weeks']},'daf':lambda:{'editions':catalogue(cfg['daf']),'calendar':data(cfg['daf']+'data/daf-calendar.json')},'music':lambda:music_collections(cfg['sanhedrin']),'qa':lambda:qa_cards(cfg['sanhedrin'],cfg.get('qa_per_language',9))}
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
  pending={ex.submit(fn):k for k,fn in tasks.items()}
  for f in concurrent.futures.as_completed(pending):
   key=pending[f]
   try:result[key]=f.result();result['status'][key]={'state':'ok','checked_at':iso(now)}
   except Exception as e:result['status'][key]={'state':'cached' if key in old else 'unavailable','error':str(e)[:160],'checked_at':iso(now)}
 if isinstance(result.get('music'),list):
  collections=result['music']
  if collections and 'tracks' not in collections[0]:
   with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    pending={ex.submit(music_seed,c):c for c in collections};complete=[]
    for f,c in pending.items():
     try:complete.append(f.result())
     except Exception as e:
      cached=next((x for x in old.get('music',[]) if x['id']==c['id']),None)
      complete.append(cached or dict(c,tracks=[],playlists=[],series=[]))
   result['music']=complete
 if result.get('zohar'):
  try:result['zohar']['preview']=study_preview(cfg['zohar'],result['zohar']['editions'])
  except Exception:pass
 save(ROOT/'data/ecosystem.json',result)
 print('MORIAH integrations:',json.dumps({'status':result['status'],'music_collections':len(result.get('music',[])),'tracks':sum(len(c.get('tracks',[])) for c in result.get('music',[])),'qa_cards':len(result.get('qa',{}).get('cards',[]))},ensure_ascii=False))
 return result

if __name__=='__main__':collect()
