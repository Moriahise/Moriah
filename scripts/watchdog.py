#!/usr/bin/env python3
"""Bounded recovery of stale/failed publications using this repository's token."""
import json,os,re
from datetime import datetime,timedelta
from urllib.request import Request,urlopen
from pipeline import ROOT,UTC,load,parse_date,iso
from publication import public_json,freshness

RECOVERY_PREFIX='MORIAH recovery'
ACTIVE={'queued','in_progress','pending','waiting','requested'}

def decision(runs,data,health,now):
    recent=[r for r in runs if now-parse_date(r['created_at'])<timedelta(hours=6) and r.get('display_title','').startswith(RECOVERY_PREFIX)]
    active=[r for r in runs if r.get('status') in ACTIVE]
    if active:
        stuck=[r for r in active if r.get('status')=='in_progress' and now-parse_date(r.get('run_started_at') or r['created_at'])>timedelta(minutes=45)]
        if stuck:return {'action':'cancel_only' if len(recent)>=3 else 'cancel_and_recover','run_id':stuck[0]['id'],'reason':'Publication exceeded 45 minutes; recovery budget is bounded'}
        return {'action':'wait','reason':'A publication is already queued or running'}
    latest=runs[0] if runs else {};finished=parse_date(latest.get('updated_at'))
    if latest.get('conclusion')=='success' and finished and now-finished<timedelta(minutes=10):return {'action':'wait','reason':'Allowing the new Pages deployment to propagate'}
    problems=freshness(data,health,now)
    if latest.get('conclusion') in ('failure','timed_out','startup_failure'):problems.insert(0,'Latest publication failed')
    if not problems:return {'action':'healthy','reason':'Published news and source health are current'}
    if len(recent)>=3:return {'action':'limited','reason':'Three recovery attempts in six hours; the next scheduled collection can try again'}
    return {'action':'recover','reason':'; '.join(problems)}

class GitHub:
    def __init__(self,repo,token):
        if not re.fullmatch(r'[\w.-]+/[\w.-]+',repo):raise ValueError('Invalid repository')
        self.base='https://api.github.com/repos/'+repo+'/';self.token=token
    def request(self,path,body=None):
        req=Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+self.token,'Accept':'application/vnd.github+json','Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'MORIAH-publication-watchdog'},method='POST' if body is not None else 'GET')
        with urlopen(req,timeout=25) as r:
            content=r.read();return json.loads(content) if content else {}

def execute(api,plan):
    if plan['action'] in ('cancel_only','cancel_and_recover'):api.request('actions/runs/'+str(plan['run_id'])+'/cancel',{})
    if plan['action'] in ('recover','cancel_and_recover'):
        api.request('actions/workflows/newspaper.yml/dispatches',{'ref':'main','inputs':{'recovery':True}})
        return 'Dispatched fresh-main recovery: cached translations, validated feeds and preserved study cache.'
    return plan['reason']

def main():
    token=os.getenv('GITHUB_TOKEN');repo=os.getenv('GITHUB_REPOSITORY','Moriahise/Moriah')
    if not token:raise RuntimeError('Repository Actions token is required')
    api=GitHub(repo,token);now=datetime.now(UTC);base=load(ROOT/'config/settings.json')['base_url']
    runs=api.request('actions/workflows/newspaper.yml/runs?per_page=40')['workflow_runs']
    try:data=public_json(base,'data/latest.json',int(now.timestamp()))
    except Exception:data={}
    try:health=public_json(base,'data/health.json',int(now.timestamp()))
    except Exception:health={'state':'degraded'}
    plan=decision(runs,data,health,now);result=execute(api,plan)
    summary='## MORIAH publication watchdog\n\n'+iso(now)+' · '+plan['action']+'\n\n'+plan['reason']+'\n\n'+result+'\n'
    print(summary)
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(summary)
    if plan['action']=='limited':print('::warning::Recovery rate limit reached; source failures remain visible in publication status.')

if __name__=='__main__':main()
