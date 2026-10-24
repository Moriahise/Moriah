#!/usr/bin/env python3
"""MORIAH: bounded RSS/Atom ingestion, local translation and immutable weekly editions.
No publisher article pages, paywalls or video streams are downloaded.
"""
from __future__ import annotations
import argparse, concurrent.futures, hashlib, html, json, os, re, shutil, sys, tempfile, time, zipfile
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
UTC=timezone.utc
MAX_BYTES=4_000_000
UA='MORIAH/1.0 (+https://github.com/Moriahise/Moriah; RSS/Atom headlines only)'
ATOM='{http://www.w3.org/2005/Atom}'
YT='{http://www.youtube.com/xml/schemas/2015}'
MEDIA='{http://search.yahoo.com/mrss/}'

def load(path,default=None):
    p=Path(path)
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default

def save(path,data):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(p)

def iso(d): return d.astimezone(UTC).isoformat(timespec='seconds').replace('+00:00','Z')

def parse_date(s):
    if not s:return None
    try:
        d=datetime.fromisoformat(s.strip().replace('Z','+00:00'))
    except ValueError:
        try:
            from email.utils import parsedate_to_datetime
            d=parsedate_to_datetime(s.strip())
        except (ValueError,TypeError,OverflowError):return None
    return d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC)

class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,t,a):
        if t in ('script','style'):self.skip+=1
    def handle_endtag(self,t):
        if t in ('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,t):
        if not self.skip:self.parts.append(t)

def plain(s,limit=300):
    p=Text();p.feed(html.unescape(str(s or '')))
    return re.sub(r'\s+',' ',' '.join(p.parts)).strip()[:limit]

def safe_url(s):
    try:
        p=urlsplit(s)
        return p.scheme=='https' and bool(p.hostname) and not p.username and not p.password and not p.port
    except (ValueError,TypeError):return False

def canonical(url):
    p=urlsplit(url)
    q=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k not in ('fbclid','gclid','ref','source')]
    return urlunsplit(('https',p.netloc.lower(),p.path,urlencode(q),'')).rstrip('/')

def host_allowed(link,source):
    if not safe_url(link):return False
    h=urlsplit(link).hostname.removeprefix('www.')
    domains=source.get('allowed_domains') or [urlsplit(source['homepage']).hostname.removeprefix('www.')]
    return any(h==d or h.endswith('.'+d) for d in domains)

def fetch(url,timeout=18,headers=None):
    if not safe_url(url):raise ValueError('HTTPS URL required')
    # Configured publisher feeds only. No input URL comes from a visitor.
    req=Request(url,headers={'User-Agent':UA,'Accept':'application/atom+xml,application/rss+xml,application/xml,application/json,text/xml;q=0.9,*/*;q=0.2',**(headers or {})})
    for attempt in range(2):
        try:
            with urlopen(req,timeout=timeout) as r:
                b=r.read(MAX_BYTES+1)
                if len(b)>MAX_BYTES:raise ValueError('Response exceeds 4 MB')
                if not safe_url(r.url):raise ValueError('Unsafe redirect')
                return b,dict(r.headers)
        except HTTPError as e:
            if e.code in (429,500,502,503,504) and attempt==0:time.sleep(1);continue
            raise
        except (TimeoutError,URLError):
            if attempt==0:continue
            raise

def language(s,fallback='en'):
    counts={c:len(re.findall(p,s)) for c,p in {'he':r'[\u0590-\u05ff]','ar':r'[\u0600-\u06ff]','ru':r'[\u0400-\u04ff]','en':r'[A-Za-z]'}.items()}
    return max(counts,key=counts.get) if max(counts.values())>=3 else fallback

def parse_feed(data,source,now=None):
    now=now or datetime.now(UTC)
    if re.search(br'<!\s*(DOCTYPE|ENTITY)',data.replace(b'\x00',b''),re.I):raise ValueError('DTD/entity XML rejected')
    try:root=ET.fromstring(data)
    except (ET.ParseError,LookupError,ValueError):
        # Some first-party feeds declare UTF-16 while transmitting UTF-8.
        text=data.decode('utf-8-sig')
        text=re.sub(r'^\s*<\?xml[^?]*\?>','',text)
        root=ET.fromstring(text)
    entries=root.findall('.//item')
    if not entries:entries=root.findall(ATOM+'entry')
    if root.tag not in ('rss',ATOM+'feed','{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF') and not entries:raise ValueError('No RSS/Atom feed')
    result=[]
    for e in entries:
        title=plain(e.findtext('title') or e.findtext(ATOM+'title'))
        link=e.findtext('link')
        if not link:
            link=next((a.attrib.get('href') for a in e.findall(ATOM+'link') if a.attrib.get('rel','alternate')=='alternate'),None)
        if not title or not link or not host_allowed(link,source):continue
        d=parse_date(e.findtext('pubDate') or e.findtext(ATOM+'published') or e.findtext(ATOM+'updated') or e.findtext('{http://purl.org/dc/elements/1.1/}date'))
        if d and d>now+timedelta(minutes=15):continue
        url=canonical(link)
        item={'id':hashlib.sha256(url.encode()).hexdigest()[:20],'title':title,'titles':{},'source_id':source['id'],'family':source['family'],'section':source['section'],'source_language':language(title,source['language']),'url':url,'published_at':iso(d) if d else None,'observed_at':iso(now),'type':source.get('type','news'),'translation':{},'provenance':'publisher_feed'}
        vid=e.findtext(YT+'videoId')
        if vid and re.fullmatch(r'[\w-]{11}',vid):item.update(video_id=vid,type='video')
        item['titles'][item['source_language']]=title
        result.append(item)
    return result

RULES=[('opinion',r'\b(opinion|editorial|commentary)\b|פרשנות|דעה'),('parashah',r'\b(parasha[h]?|torah portion)\b|פרשת השבוע'),('halakhah',r'\b(halacha|halakha|kosher|kashrut)\b|הלכה|כשרות'),('archaeology',r'\b(archaeolog|excavation|inscription)\w*|ארכיאולוג|ארכאולוג|חפירות'),('science',r'\b(scien|research|medical|medicine|health|cancer)\w*|מחקר|רפואה|בריאות'),('nature',r'\b(climate|environment|wildlife|water|ecology)\w*|סביבה|טבע|אקלים'),('economy',r'\b(econom|bank|financ|inflation|business|stock|startup)\w*|כלכל|בורסה|שקל|נדל״ן|נדל"ן'),('diaspora',r'\b(diaspora|antisemit|synagogue|jewish community)\w*|אנטישמ|תפוצות'),('culture',r'\b(music|book|art|culture|film|festival|poetry)\w*|תרבות|מוזיקה|מוסיקה|ספרות'),('security',r'\b(iran|idf|army|hostage|missile|defense|ceasefire|diplomacy)\w*|ביטחון|צה״ל|צה"ל|איראן|חטופ'),('jerusalem',r'\b(jerusalem|temple mount)\b|ירושלים|המקדש')]
def classify(title,default):
    if default not in ('israel','week','security'):return default
    return next((sec for sec,p in RULES if re.search(p,title,re.I)),default)

def poll(source,now):
    status={'id':source['id'],'checked_at':iso(now),'state':'directory','items':0,'error':None}
    if not source.get('enabled',True):status['state']='disabled';return [],status
    if not source.get('feed_urls'):return [],status
    failures=[]
    for url in source['feed_urls']:
        try:
            data,headers=fetch(url)
            items=parse_feed(data,source,now)
            items=[x for x in items if x['published_at'] and parse_date(x['published_at'])>=now-timedelta(days=21)]
            if not items:failures.append('No dated entries from the last 21 days');continue
            for x in items:x['section']=classify(x['title'],source['section'])
            status.update(state='ok',items=len(items),feed_url=url,last_success_at=iso(now),latest_at=max(x['published_at'] for x in items))
            return items[:source.get('max_items',15)],status
        except Exception as e:failures.append(type(e).__name__+': '+str(e)[:100])
    status.update(state='unavailable',error='; '.join(failures)[:250])
    return [],status

class Translator:
    """Local OPUS/Argos CTranslate2 models; cached, no API key or paid API."""
    versions={'en_he':'1_5','he_en':'1_5','ru_en':'1_9','ar_en':'1_0'}
    def __init__(self,cache=None):
        self.root=Path(cache or os.environ.get('MORIAH_MODEL_CACHE',str(Path.home()/'.cache/moriah-models')))
        self.loaded={}
    def model(self,pair):
        if pair in self.loaded:return self.loaded[pair]
        import ctranslate2,sentencepiece
        version=self.versions[pair];folder=self.root/('translate-'+pair+'-'+version)
        if pair=='ar_en':folder=self.root/'ar_en'
        if not (folder/'model/model.bin').exists():
            self.root.mkdir(parents=True,exist_ok=True)
            failures=[]
            for host in ('https://argos-net.com/v1/','https://data.argosopentech.com/argospm/v1/'):
                try:
                    name='translate-'+pair+'-'+version+'.argosmodel'
                    req=Request(host+name,headers={'User-Agent':UA})
                    with urlopen(req,timeout=90) as r, tempfile.TemporaryFile() as f:
                        count=0
                        while b:=r.read(1_048_576):
                            count+=len(b)
                            if count>350_000_000:raise ValueError('Oversized model')
                            f.write(b)
                        f.seek(0)
                        with zipfile.ZipFile(f) as z:
                            for info in z.infolist():
                                target=(self.root/info.filename).resolve()
                                if not target.is_relative_to(self.root.resolve()) or (info.external_attr>>16)&0o170000==0o120000:raise ValueError('Unsafe model archive')
                            z.extractall(self.root)
                    break
                except Exception as e:failures.append(str(e)[:90])
            if not (folder/'model/model.bin').exists():raise RuntimeError('Model unavailable: '+'; '.join(failures))
        sp=sentencepiece.SentencePieceProcessor(model_file=str(folder/'sentencepiece.model'))
        tr=ctranslate2.Translator(str(folder/'model'),device='cpu',compute_type='int8',inter_threads=1,intra_threads=2)
        self.loaded[pair]=(sp,tr);return sp,tr
    def translate_many(self,texts,src,dst):
        pair=src+'_'+dst
        if pair not in self.versions:
            if src not in ('ar','ru') or dst!='he':raise ValueError('Unsupported language')
            return self.translate_many(self.translate_many(texts,src,'en'),'en','he')
        sp,tr=self.model(pair)
        encoded=[sp.encode(t,out_type=str) for t in texts]
        results=tr.translate_batch(encoded,beam_size=3,max_decoding_length=160,max_input_length=256,batch_type='tokens',max_batch_size=512,repetition_penalty=1.12)
        return [sp.decode(r.hypotheses[0]).strip() for r in results]

def valid_translation(src,dst,lang):
    if not dst or not 2<=len(dst)<=450 or language(dst,lang)!=lang:return False
    # Digits in names/dates are not silently changed by a translation model.
    if set(re.findall(r'\d+',src))!=set(re.findall(r'\d+',dst)):return False
    words=dst.split()
    return not (len(words)>8 and len(set(words))<len(words)/3)

def enrich(items,cache,limit,enabled=True,translator=None):
    queue={}
    for item in items:
        src=item['source_language'];item['titles']={src:item['title']};item['translation']={}
        for dst in ('en','he'):
            if src==dst:continue
            key=hashlib.sha256((src+'|'+dst+'|'+item['title']).encode()).hexdigest()
            if key in cache and valid_translation(item['title'],cache[key],dst):
                item['titles'][dst]=cache[key];item['translation'][dst]='machine'
            elif enabled and limit>0 and src in ('en','he','ar','ru'):
                queue.setdefault((src,dst),[]).append((item,key));limit-=1
    errors=[]
    if queue:
        translator=translator or Translator()
        for (src,dst),records in queue.items():
            try:
                values=translator.translate_many([x['title'] for x,k in records],src,dst)
                for (item,key),value in zip(records,values):
                    if valid_translation(item['title'],value,dst):
                        cache[key]=value;item['titles'][dst]=value;item['translation'][dst]='machine'
            except Exception as e:errors.append(src+'->'+dst+': '+type(e).__name__+': '+str(e)[:130])
    return errors

def calendar(settings,now,previous):
    result={};day=now.astimezone(ZoneInfo('Asia/Jerusalem')).date()
    # The next Shabbat is deliberate, independent of Hebcal's rolling Sunday boundary.
    shabbat=day+timedelta(days=(5-day.weekday())%7)
    for city in settings['cities']:
        url='https://www.hebcal.com/shabbat?'+urlencode(dict(cfg='json',geonameid=city['geonameid'],M='on',b=40 if city['id']=='jerusalem' else 18,gy=shabbat.year,gm=shabbat.month,gd=shabbat.day,i='on' if city['israel'] else 'off',lg='s',leyning='on'))
        try:
            b,_=fetch(url);d=json.loads(b)
            if not d.get('items') or not d.get('location'):raise ValueError('Invalid calendar response')
            result[city['id']]={'city':city,'fetched_at':iso(now),'shabbat_date':str(shabbat),'stale':False,'data':d,'method':{'candle_minutes':40 if city['id']=='jerusalem' else 18,'havdalah_degrees':8.5},'url':url}
        except Exception:
            if city['id'] in previous:result[city['id']]={**previous[city['id']],'stale':True}
    return result

def learning_calendar(now,previous):
    day=now.astimezone(ZoneInfo('Asia/Jerusalem')).date()
    url='https://www.hebcal.com/hebcal?'+urlencode(dict(v=1,cfg='json',start=str(day),end=str(day+timedelta(days=6)),F='on',i='on',lg='s'))
    try:
        b,_=fetch(url);data=json.loads(b)
        items=[x for x in data.get('items',[]) if x.get('category')=='dafyomi']
        if not items:raise ValueError('No daily learning data')
        return {'fetched_at':iso(now),'items':items,'stale':False,'source':'Hebcal · CC BY 4.0'}
    except Exception:return {**previous,'stale':True} if previous else {'items':[],'stale':True}

def issue_features(features,issue_id,launch):
    if launch:return features[:10]
    fixed=[a for a in features if a['section'] in ('halakhah','daf','parashah')]
    rotating=[a for a in features if a['section'] not in ('halakhah','daf','parashah')]
    week=datetime.fromisoformat(issue_id).isocalendar().week
    start=(week*7)%len(rotating)
    chosen=[rotating[(start+i)%len(rotating)] for i in range(7)]
    return [chosen[0]]+fixed+chosen[1:]

def due_issue(now,launch_date):
    local=now.astimezone(ZoneInfo('Asia/Jerusalem'))
    days=(local.weekday()-2)%7
    w=(local-timedelta(days=days)).replace(hour=18,minute=0,second=0,microsecond=0)
    if local<w:w-=timedelta(days=7)
    if str(w.date())<launch_date:return launch_date+'-launch',True
    return str(w.date()),False

def diversify(items,limit=24,per_family=3):
    out=[];counts={}
    for item in items:
        family=item['family']
        if counts.get(family,0)>=per_family:continue
        out.append(item);counts[family]=counts.get(family,0)+1
        if len(out)>=limit:break
    return out

def validate(payload):
    assert payload['schema_version']==1
    ids=set();known={s['id'] for s in payload['sources']};sections={s['id'] for s in payload['sections']}
    for item in payload['news']+payload['videos']:
        assert item['id'] not in ids,'Duplicate article ID';ids.add(item['id'])
        assert item['source_id'] in known and item['section'] in sections
        assert safe_url(item['url']) and item['title']
        assert item['source_language'] in item['titles']
        assert item.get('published_at') and parse_date(item['published_at'])
    assert all(a.get('title',{}).get('he') and a.get('title',{}).get('en') for a in payload['features'])
    return True

def main():
    p=argparse.ArgumentParser();p.add_argument('--offline',action='store_true');p.add_argument('--no-translate',action='store_true');p.add_argument('--now');args=p.parse_args()
    now=parse_date(args.now) if args.now else datetime.now(UTC)
    settings=load(ROOT/'config/settings.json');sources=load(ROOT/'config/sources.json')+load(ROOT/'config/channels.json',[])
    previous=load(ROOT/'data/latest.json',{})
    old={x['id']:x for x in previous.get('source_status',[])}
    retained=previous.get('news',[])+previous.get('videos',[]);known={x['id'] for x in sources};byid={x['id']:x for x in retained if x['source_id'] in known}
    statuses=[]
    if not args.offline:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            for items,status in ex.map(lambda s:poll(s,now),sources):
                last=old.get(status['id'],{})
                if status['state']!='ok' and last.get('last_success_at'):status['last_success_at']=last['last_success_at']
                statuses.append(status)
                for x in items:byid[x['id']]=x
                print(status['id'],status['state'],status['items'],flush=True)
    else:statuses=previous.get('source_status',[])
    cutoff=now-timedelta(days=settings.get('retention_days',21))
    items=sorted([x for x in byid.values() if x.get('published_at') and cutoff<=parse_date(x['published_at'])<=now+timedelta(minutes=15)],key=lambda x:x['published_at'],reverse=True)
    news=[x for x in items if x['type']!='video'][:settings.get('max_news',360)]
    videos=diversify([x for x in items if x['type']=='video'],72,8)
    cache=load(ROOT/'data/translations.json',{})
    # Newest news across independent source families gets first translation budget.
    priority=diversify(news,100,10)+videos[:32]
    priority_ids={x['id'] for x in priority}
    rest=[x for x in news+videos if x['id'] not in priority_ids]
    errors=enrich(priority+rest,cache,settings.get('max_translations_per_run',240),not args.no_translate and settings.get('translate',True))
    # Bound the persistent translation cache; values are plain text only.
    if len(cache)>12000:cache=dict(list(cache.items())[-10000:])
    save(ROOT/'data/translations.json',cache)
    cals=previous.get('calendars',{}) if args.offline else calendar(settings,now,previous.get('calendars',{}))
    features=load(ROOT/'content/features.json',[])
    payload={'schema_version':1,'generated_at':iso(now),'timezone':'Asia/Jerusalem','news':news,'videos':videos,'features':features,'learning_calendar':previous.get('learning_calendar',{}) if args.offline else learning_calendar(now,previous.get('learning_calendar',{})),'sections':load(ROOT/'config/sections.json'),'sources':sources,'source_status':statuses,'calendars':cals,'translation_engine':'OPUS / Argos · local CTranslate2','translation_errors':errors,'counts':{'news':len(news),'videos':len(videos),'active_sources':sum(s['state']=='ok' for s in statuses),'configured_sources':len(sources),'translated_news':sum('en' in x['titles'] and 'he' in x['titles'] for x in news)}}
    validate(payload)
    # Never replace the last good edition by an empty/failed live collection.
    if not news and not args.offline:
        save(ROOT/'data/health.json',{'checked_at':iso(now),'state':'degraded','source_status':statuses,'message':'No usable recent feeds; last successful edition preserved.'})
        if previous:print('No recent news: previous payload retained');return
    save(ROOT/'data/latest.json',payload)
    save(ROOT/'data/health.json',{'checked_at':iso(now),'state':'ok' if news else 'initializing','counts':payload['counts'],'translation_errors':errors})
    issue_id,launch=due_issue(now,settings['launch_date'])
    issue_path=ROOT/'data/issues'/f'{issue_id}.json'
    if not issue_path.exists() and news:
        issue={'id':issue_id,'published_at':iso(now),'launch':launch,'news':diversify(news,32,4),'videos':diversify(videos,8,1),'features':issue_features(features,issue_id,launch),'learning_calendar':payload['learning_calendar'],'calendars':cals,'source_status':statuses,'sources':sources,'sections':payload['sections'],'automated':True,'revision':1}
        save(issue_path,issue)
    issues=[]
    for path in sorted((ROOT/'data/issues').glob('*.json'),reverse=True) if (ROOT/'data/issues').exists() else []:
        i=load(path);issues.append({'id':i['id'],'published_at':i['published_at'],'launch':i['launch'],'revision':i['revision']})
    save(ROOT/'data/issues.json',issues)
    summary=f"## MORIAH\n\nCollected: {len(news)} recent news links and {len(videos)} videos.\n\nWorking feeds: {payload['counts']['active_sources']}/{len(sources)}. Fully bilingual headlines: {payload['counts']['translated_news']}/{len(news)}.\n\nAutomated compilation; no human or rabbinic review claimed.\n"
    if errors:summary+='\nTranslation warnings: '+', '.join(errors)+'\n'
    for s in statuses:
        if s['state']=='unavailable':summary+=f"\n- {s['id']}: {s['error']}\n"
    (ROOT/'data/run-report.md').write_text(summary)
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(summary)
    print(summary)

if __name__=='__main__':main()
