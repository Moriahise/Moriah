#!/usr/bin/env python3
"""Publish a run marker and verify what GitHub Pages actually serves."""
import argparse,json,os,time
from datetime import datetime,timedelta
from pipeline import ROOT,UTC,load,save,fetch,parse_date,iso,validate

def freshness(data,health,now):
    problems=[];generated=parse_date(data.get('generated_at'))
    if not generated or now-generated>timedelta(hours=8):problems.append('Public collection is older than 8 hours')
    latest=max((parse_date(x.get('published_at')) for x in data.get('news',[]) if parse_date(x.get('published_at'))),default=None)
    if not latest or now-latest>timedelta(hours=36):problems.append('No news from the last 36 hours')
    if health.get('state')=='degraded':problems.append('Source collection is degraded')
    return problems

def public_json(base,path,tag='check'):
    return json.loads(fetch(base+path+'?moriah_check='+str(tag),timeout=12,headers={'Cache-Control':'no-cache'})[0])

def prepare():
    data=load(ROOT/'data/latest.json');validate(data);health=load(ROOT/'data/health.json',{})
    marker={'schema':1,'run_id':os.getenv('GITHUB_RUN_ID','local'),'run_attempt':os.getenv('GITHUB_RUN_ATTEMPT','1'),'built_at':iso(datetime.now(UTC)),'generated_at':data['generated_at'],'latest_news_at':max((x['published_at'] for x in data['news']),default=None),'news':len(data['news']),'source_state':health.get('state'),'mode':'recovery' if os.getenv('MORIAH_RECOVERY')=='true' else 'normal'}
    save(ROOT/'data/publication.json',marker);print(json.dumps(marker))

def verify(run_id,attempts=6):
    base=load(ROOT/'config/settings.json')['base_url'];last=''
    for n in range(attempts):
        try:
            marker=public_json(base,'data/publication.json',str(run_id)+'-'+str(n))
            if str(marker.get('run_id'))!=str(run_id):raise ValueError('Pages is still serving a previous publication')
            if os.getenv('GITHUB_RUN_ATTEMPT') and str(marker.get('run_attempt'))!=os.environ['GITHUB_RUN_ATTEMPT']:raise ValueError('Pages is still serving a previous run attempt')
            data=public_json(base,'data/latest.json',str(run_id)+'-'+str(n));validate(data)
            if data['generated_at']!=marker['generated_at']:raise ValueError('Pages marker and source data are inconsistent')
            print('Verified live publication:',run_id,data['generated_at'],len(data['news']),'headlines');return marker
        except Exception as e:
            last=type(e).__name__+': '+str(e)[:180]
            if n+1<attempts:time.sleep(5)
    raise RuntimeError(last)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','verify']);p.add_argument('--run-id',default=os.getenv('GITHUB_RUN_ID','local'));a=p.parse_args()
    prepare() if a.command=='prepare' else verify(a.run_id)
