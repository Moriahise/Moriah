#!/usr/bin/env python3
"""Build static web pages and the frozen, bilingual 16-page weekly PDFs."""
from __future__ import annotations
import argparse,html,json,re,shutil,sys,hashlib
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
from xml.sax.saxutils import escape as xml_escape
from pipeline import ROOT,load,validate,safe_url

def esc(s):return html.escape(str(s or ''),quote=True)
def asset_version(name):return hashlib.sha256((ROOT/'assets'/name).read_bytes()).hexdigest()[:12]
def tr(lang,en,he):return he if lang=='he' else en

def page(title,body,lang='en',prefix='',extra=''):
    return f'''<!doctype html><html lang="{lang}" dir="{'rtl' if lang=='he' else 'ltr'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} | MORIAH</title><link rel="icon" href="{prefix}assets/mark.svg"><link rel="stylesheet" href="{prefix}assets/style.css?v={asset_version('style.css')}">{extra}</head><body><div class="policy-page"><a class="footer-brand" href="{prefix}index.html?lang={lang}">MORIAH · מוריה</a>{body}</div></body></html>'''

def source_names(issue,lang):return {s['id']:s['name'][lang] for s in issue['sources']}
def item_title(x,lang):return x['titles'].get(lang,x['title'])
def news_list(items,issue,lang,full=False):
    names=source_names(issue,lang);out=[]
    for x in items:
        translated=x.get('translation',{}).get(lang)=='machine'
        label=tr(lang,'Machine translation','תרגום מכונה') if translated else x['source_language'].upper()
        original=f'<div class="original" dir="auto">{esc(x["title"])}</div>' if full and translated else ''
        out.append(f'<li><span class="source">{esc(names.get(x["source_id"],x["source_id"]))} · {esc(x["published_at"][:10])}</span><a href="{esc(x["url"])}">{esc(item_title(x,lang))}</a><small>{esc(label)}</small>{original}</li>')
    return '<ul class="news-list">'+''.join(out)+'</ul>'

def feature_body(a,lang):
    refs=''.join(f'<li><a href="{esc(s["url"])}">{esc(s["label"])}</a></li>' for s in a['sources'])
    return f'<div class="eyebrow">{tr(lang,"FROM THE MORIAH LEARNING LIBRARY · AI-ASSISTED","מתוך ספריית הלימוד של מוריה · בסיוע בינה מלאכותית")}</div><h2>{esc(a["title"][lang])}</h2><p class="deck">{esc(a["deck"][lang])}</p>'+''.join(f'<p>{esc(p)}</p>' for p in a['body'][lang])+f'<div class="references"><strong>{tr(lang,"Sources for further reading","מקורות להמשך קריאה")}</strong><ul>{refs}</ul></div>'

PRINT_CSS='''
@page{size:A4;margin:17mm 17mm 18mm;@bottom-left{content:"MORIAH | מוריה";font:8pt "DejaVu Sans";color:#6d7476}@bottom-right{content:counter(page);font:8pt "DejaVu Sans";color:#6d7476}}
*{box-sizing:border-box}body{margin:0;color:#142c3d;font-family:"DejaVu Sans",sans-serif;font-size:10.3pt;line-height:1.7}h1,h2,h3,p{margin-top:0}h1{font-size:35pt;line-height:1.2;font-weight:400;margin:18mm 0 7mm}h2{font-size:25pt;line-height:1.3;font-weight:400;margin:8mm 0 6mm}h3{font-size:15pt;line-height:1.4}p{margin-bottom:5mm}a{color:#142c3d;text-decoration:none;overflow-wrap:anywhere}.sheet{break-after:page;min-height:250mm}.sheet:last-child{break-after:auto}.folio-head{display:flex;justify-content:space-between;border-top:2px solid #142c3d;border-bottom:1px solid #b8b4a7;padding:3mm 0;font-size:8pt}.folio-head strong{letter-spacing:.1em}.eyebrow{font-size:8pt;color:#94713d;letter-spacing:.04em;text-transform:uppercase;margin-top:6mm}.deck{font-size:13pt;line-height:1.7;color:#5f6d72;margin-bottom:8mm}.mast{font-size:49pt;font-weight:bold;line-height:1.15;letter-spacing:-.06em;border-bottom:3px double #142c3d;padding:5mm 0 6mm;margin-bottom:8mm;direction:ltr;text-align:center}.mast .he{font-size:40pt;letter-spacing:0}.cover-label{font-size:11pt;color:#94713d;margin-top:8mm}.cover-title{font-size:32pt;margin-top:14mm}.cover-band{background:#142c3d;color:#f5f0e5;padding:8mm;margin-top:14mm}.cover-band h3{font-size:16pt}.cover-band p{font-size:10pt;margin:0}.news-list{padding:0;list-style:none}.news-list li{break-inside:avoid;border-top:1px solid #d9d6cc;padding:3mm 0;line-height:1.5}.news-list a{display:block;font-size:10.5pt;margin:1.5mm 0}.news-list small{font-size:7pt;color:#637079}.source{font-size:8pt;color:#94713d}.original{font-size:8pt;color:#637079;margin-top:2mm}.references{border-top:1px solid #d9d6cc;margin-top:8mm;padding-top:4mm;font-size:8pt}.references ul{padding-inline-start:5mm}.references li{margin-bottom:2mm}.notice{border-inline-start:3px solid #94713d;padding:3mm 5mm;background:#efede5;font-size:9pt;margin-block:5mm}.toc{list-style:none;padding:0}.toc li{padding:1.9mm 0;border-bottom:1px solid #d9d6cc;display:flex;justify-content:space-between;gap:5mm}.calendar-row{padding:1.8mm 0;border-bottom:1px solid #d9d6cc}.calendar-row h3{font-size:12pt;margin-bottom:1mm}.calendar-row p{font-size:9pt;margin:0}.source-columns{columns:2;column-gap:9mm;font-size:8pt}.source-columns p{break-inside:avoid}.art{height:37mm;overflow:hidden;background:#142c3d;position:relative}.art svg{width:100%;height:100%}.section-title{font-size:9pt;letter-spacing:.12em;color:#94713d;margin-top:9mm}.small{font-size:8pt;color:#637079}html[dir=rtl] body{line-height:1.9}html[dir=rtl] .deck{line-height:1.9}.web-toolbar{display:none}
@media screen{body{background:#e5e3da;padding:30px}.sheet{background:#fffdf7;width:210mm;min-height:277mm;padding:17mm;margin:0 auto 30px;box-shadow:0 3px 15px #0001}.web-toolbar{display:flex;max-width:210mm;margin:0 auto 25px;gap:20px;font-size:13px}.web-toolbar a{background:#142c3d;color:white;padding:8px 15px}.folio-head{font-size:11px}.news-list small{font-size:10px}}
@media screen and (max-width:850px){body{padding:12px}.sheet{width:100%;min-height:0;padding:24px}.mast{font-size:38px}.mast .he{font-size:32px}h1{font-size:30px}h2{font-size:28px}.source-columns{columns:1}.cover-title{font-size:30px}.web-toolbar{flex-wrap:wrap}}
'''

def make_issue(issue,lang):
    pages=[];features=issue['features'];names=source_names(issue,lang);date=issue['published_at'][:10]
    def add(section,body):
        pages.append(f'<section class="sheet"><div class="folio-head"><strong>MORIAH · מוריה</strong><span>{esc(section)}</span><span>{esc(date)}</span></div>{body}</section>')
    a=features[0]
    art='<div class="art"><svg viewBox="0 0 750 130" xmlns="http://www.w3.org/2000/svg"><circle cx="610" cy="44" r="23" fill="#c5a469"/><g fill="none" stroke="#d0b889" stroke-width="2"><path d="M0 112H40V83H85V102H120V66H175V90H215V46H260V25H300V46H337V82H388V55H440V91H480V60H530V94H580V72H630V102H690V87H750"/><path d="M0 118Q200 99 370 118T750 116"/></g></svg></div>'
    add(tr(lang,'The cover','השער'),f'<div class="mast">MORIAH <span class="he">מוריה</span></div><p style="text-align:center">{tr(lang,"The Jewish & Israel Review · Torah · People · Land","כתב עת ליהדות ולישראל · תורה · עם · ארץ")}</p>{art}<div class="cover-label">{tr(lang,"LAUNCH EDITION" if issue["launch"] else "THE WEEKLY EDITION","גיליון פתיחה" if issue["launch"] else "הגיליון השבועי")}</div><h1 class="cover-title">{esc(a["title"][lang])}</h1><p class="deck">{esc(a["deck"][lang])}</p><p>{esc(a["body"][lang][0])}</p><div class="cover-band"><h3>{tr(lang,"A wider view. A deeper conversation.","מבט רחב. שיחה מעמיקה.")}</h3><p>{tr(lang,"Inside: the source desk, Torah learning, Jerusalem, language, community and culture.","בגיליון: דסק המקורות, לימוד תורה, ירושלים, שפה, קהילה ותרבות.")}</p></div>')
    toc_en=['The cover','Inside MORIAH','The source desk','Israel & the Jewish world','One stone, a whole world','How to read a responsum','Two languages, one conversation','A window into the Daf','Israel through its numbers','Communities & traditions','Young source detectives','A melody and its journey','Reading the calendar','Reading the week with care','This Shabbat & further learning','Sources & transparency']
    toc_he=['השער','בתוך מוריה','דסק המקורות','ישראל והעולם היהודי','אבן אחת — עולם שלם','כיצד קוראים תשובה הלכתית','שתי שפות, שיחה אחת','חלון אל הדף','ישראל דרך המספרים','קהילות ומסורות','בלשי מקורות צעירים','מנגינה והדרך שעברה','קוראים את הלוח','קוראים את השבוע','השבת הקרובה והמשך הלימוד','מקורות ושקיפות']
    toc=(toc_he[:4] if lang=='he' else toc_en[:4])+[a['title'][lang] for a in features[:10]]+(toc_he[14:] if lang=='he' else toc_en[14:])
    add(toc[1],f'<div class="eyebrow">{tr(lang,"WELCOME TO MORIAH","ברוכים הבאים למוריה")}</div><h2>{tr(lang,"A home for Jewish learning, life and Israel.","בית ללימוד, לחיים יהודיים ולישראל.")}</h2><p>{tr(lang,"This edition brings together an automatically selected source desk and original bilingual reading guides from the MORIAH library. It is an invitation to follow a source, ask a better question and continue a conversation.","הגיליון מחבר בין דסק מקורות שנבחר אוטומטית לבין מדריכי קריאה מקוריים בשתי שפות מתוך ספריית מוריה. זו הזמנה ללכת אל המקור, לשאול שאלה טובה ולהמשיך בשיחה.")}</p><ul class="toc">'+''.join(f'<li><span>{esc(v)}</span><span>{i+1:02}</span></li>' for i,v in enumerate(toc))+f'</ul><p class="small">{tr(lang,"Published","פורסם")}: {esc(issue["published_at"])} · Revision {issue["revision"]}</p>')
    notice=tr(lang,'Automatically selected publisher headlines; translated lines are machine-generated. Read the linked original report. These claims have not been independently verified by MORIAH.','כותרות מו״לים שנבחרו אוטומטית; שורות מתורגמות הופקו במכונה. קראו את הדיווח המקורי המקושר. הטענות לא אומתו באופן עצמאי בידי מוריה.')
    add(toc[2],f'<h2>{toc[2]}</h2><p class="notice">{notice}</p>'+news_list(issue['news'][:5],issue,lang))
    add(toc[3],f'<h2>{toc[3]}</h2>'+news_list(issue['news'][5:11],issue,lang))
    for a in features[:10]:add(a['title'][lang],feature_body(a,lang))
    calbody=f'<h2>{toc[14]}</h2><p class="notice">{tr(lang,"Saved calendar data for this edition only. Times are local to each named city. Current times are on the website.","נתוני לוח שמורים לגיליון זה בלבד. הזמנים מקומיים לעיר המצוינת. זמנים עדכניים נמצאים באתר.")}</p>'
    for c in issue.get('calendars',{}).values():
        if c.get('stale'):continue
        p=next((x for x in c['data']['items'] if x['category']=='parashat'),{})
        vals=[]
        for category,label in [('candles',tr(lang,'Candles','הדלקת נרות')),('havdalah',tr(lang,'Havdalah','הבדלה'))]:
            x=next((x for x in c['data']['items'] if x['category']==category),None)
            if x:vals.append(label+': '+x['date'][11:16])
        calbody+=f'<div class="calendar-row"><h3>{esc(c["city"][lang])} · {esc(c["shabbat_date"])}</h3><p>{esc(p.get("hebrew" if lang=="he" else "title",""))} · {esc(" · ".join(vals))}</p><p>{esc(c["data"]["location"]["tzid"])} · {c["method"]["candle_minutes"]} min · Havdalah 8.5° · {"Israel" if c["city"]["israel"] else "Diaspora"}</p></div>'
    calbody+=f'<div class="references">Hebcal · CC BY 4.0 · <a href="https://www.hebcal.com/">hebcal.com</a></div><h3 style="margin-top:8mm">{tr(lang,"Continue your learning","ממשיכים ללמוד")}</h3><p><a href="https://moriahise.github.io/Shiurim/">Shiurim / שיעורים</a> · <a href="https://moriahise.github.io/Daf-Yomi/">Daf Yomi / הדף היומי</a> · <a href="https://moriahise.github.io/Niggun/">Niggun / ניגון</a></p>'
    add(toc[14],calbody)
    active={s['id']:s for s in issue.get('source_status',[])}
    sourcebody=''.join(f'<p><a href="{esc(s["homepage"])}">{esc(s["name"][lang])}</a> · {s["language"].upper()}</p>' for s in issue['sources'] if s.get('type')!='video')
    add(toc[15],f'<h2>{toc[15]}</h2><p>{tr(lang,"MORIAH is an automated Hebrew–English publication. News links are collected from publisher feeds. Original headlines remain available; translations may contain errors. Study guides are AI-assisted learning material, not a practical halakhic ruling. No human review is claimed.","מוריה היא הוצאה אוטומטית בעברית ובאנגלית. קישורי החדשות נאספים מעדכוני המו״לים. כותרות המקור זמינות, ובתרגומים ייתכנו שגיאות. מדריכי הקריאה נכתבו בסיוע בינה מלאכותית ונועדו ללימוד, לא לפסיקת הלכה למעשה. אין טענה לבדיקה אנושית.")}</p><div class="source-columns">{sourcebody}</div><div class="references"><strong>{tr(lang,"Credits and corrections","קרדיטים ותיקונים")}</strong><p>Calendar: Hebcal, CC BY 4.0. Translation: OPUS / Argos Open Tech / CTranslate2. Publisher content and programme rights remain with their owners. Inclusion does not imply endorsement.</p><p><a href="https://github.com/Moriahise/Moriah/issues">github.com/Moriahise/Moriah/issues</a><br><a href="https://moriahise.github.io/Moriah/">moriahise.github.io/Moriah/</a></p></div>')
    assert len(pages)==16,len(pages)
    toolbar=f'<nav class="web-toolbar"><a href="../../index.html?lang={lang}">{tr(lang,"Return to MORIAH","בחזרה למוריה")}</a><a href="MORIAH-{issue["id"]}-{lang}.pdf">PDF · {lang.upper()}</a><a href="{("he" if lang=="en" else "en")}.html">{("עברית" if lang=="en" else "English")}</a></nav>'
    return f'<!doctype html><html lang="{lang}" dir="{"rtl" if lang=="he" else "ltr"}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORIAH · {esc(issue["id"])} · {lang.upper()}</title><style>{PRINT_CSS}</style></head><body>{toolbar}'+''.join(pages)+'</body></html>'

POLICIES='''<h1>Sources, privacy & editorial policy<br>מקורות, פרטיות ומדיניות מערכת</h1>
<h2>What this newspaper publishes / מה העיתון מפרסם</h2><p>MORIAH collects dated headline links from publisher RSS/Atom feeds and metadata from identified YouTube channels. It does not download publisher article bodies, bypass subscriptions, copy videos or present a channel as a partner. Source claims remain attributed. A working feed is not an independent fact check.</p><p dir="rtl" lang="he">מוריה אוספת קישורי כותרות מתוארכים מעדכוני המו״לים ומידע מערוצי יוטיוב מזוהים. אין הורדה של כתבות מלאות, עקיפת מנויים, העתקת סרטונים או הצגת מקור כשותף. הטענות מיוחסות למקור; עדכון תקין אינו בדיקת עובדות עצמאית.</p>
<h2>Translation & learning / תרגום ולימוד</h2><p>Translations use locally executed OPUS/Argos neural models through CTranslate2. A machine translation may be wrong, particularly with names, idioms or specialist terms. The original headline is retained. Reading guides are AI-assisted, bilingual library material; they do not claim human or rabbinic review. No human author or reviewer is invented.</p><p dir="rtl" lang="he">התרגומים מופקים במודלי OPUS/Argos מקומיים ועלולים לשגות, במיוחד בשמות ובמונחים. כותרת המקור נשמרת. מדריכי הלימוד נכתבו בסיוע בינה מלאכותית; אין טענה לבדיקה אנושית או רבנית ואין המצאה של מחבר או בודק.</p>
<h2>Calendar / לוח וזמנים</h2><p>Calendar data: <a href="https://www.hebcal.com/home/developer-apis">Hebcal</a>, <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Dates and times are displayed for a named place, local time zone and Israel/Diaspora cycle. Candle lighting: 40 minutes before sunset in Jerusalem, 18 minutes in the other configured cities. Havdalah: 8.5 degrees. Other community customs may differ. Outdated saved times are not displayed as current.</p><p dir="rtl" lang="he">נתוני הלוח: Hebcal ברישיון CC BY 4.0. מוצגים מקום, אזור זמן ומחזור ישראל או תפוצות. הדלקת נרות: 40 דקות לפני השקיעה בירושלים ו־18 דקות בערים האחרות שהוגדרו. הבדלה: 8.5 מעלות. מנהגי קהילות עשויים להיות שונים. זמנים שמורים שהתיישנו אינם מוצגים כעדכניים.</p>
<h2>Privacy / פרטיות</h2><p>No account, advertising tracker or analytics service is included. Language and city choices are stored in your browser only. Hosting providers receive ordinary network requests. Video thumbnails are loaded from YouTube when the video section is viewed; pressing play connects to YouTube’s privacy-enhanced player. YouTube controls advertisements, subtitles, availability and its own data processing. External links open the publisher’s site.</p><p dir="rtl" lang="he">אין חשבון משתמש, שירות ניתוח גלישה או מעקב פרסומי מובנה. בחירת השפה והעיר נשמרת בדפדפן בלבד. ספק האירוח מקבל בקשות רשת רגילות. תמונות הסרטונים נטענות מיוטיוב; הפעלה יוצרת חיבור לנגן הפרטיות המוגברת של יוטיוב. יוטיוב אחראית לפרסומות, כתוביות, זמינות ועיבוד המידע שלה. קישורים חיצוניים מובילים לאתר המקור.</p>
<h2>Editions & corrections / גיליונות ותיקונים</h2><p>The news desk is refreshed approximately every four hours. Weekly issues are frozen snapshots, normally published after 18:00 Asia/Jerusalem on Wednesday. GitHub schedules may be delayed. An archived issue is not today’s news. Corrections must preserve the original issue and publish a documented revision. <a href="https://github.com/Moriahise/Moriah/issues/new">Report a correction or a rights concern here.</a> Do not post private personal information in a public issue.</p><p dir="rtl" lang="he">הדסק מתעדכן בקירוב בכל ארבע שעות. גיליון שבועי הוא תמונת מצב שמורה, המופקת בדרך כלל ביום רביעי אחרי 18:00 לפי שעון ירושלים. תזמוני GitHub עשויים להתעכב. גיליון מהארכיון אינו חדשות היום. תיקון מהותי דורש גרסה מתועדת תוך שמירת הגיליון הקודם. פניות תיקון וזכויות מתקבלות בקישור לעיל; אין לפרסם בו מידע אישי פרטי.</p>
<h2>Credits / קרדיטים</h2><p>Original publisher and programme rights remain with their owners. Translation models: Argos Open Tech, OPUS/OPUS-MT and their contributors; <a href="https://github.com/argosopentech/argospm-index">model catalogue</a>. Inference: <a href="https://opennmt.net/CTranslate2/">CTranslate2</a>. Each model’s supplied README/metadata accompanies the cached installation; software and model licences are distinct. Illustrations: original MORIAH vector artwork. No endorsement by a named institution is implied.</p>'''

def build(out,pdfs):
    data=load(ROOT/'data/latest.json');validate(data)
    if out.exists():shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copytree(ROOT/'assets',out/'assets')
    shutil.copytree(ROOT/'data',out/'data',ignore=shutil.ignore_patterns('translations.json','run-report.md'))
    index=(ROOT/'web/index.html').read_text()
    fallback='<ul>'+''.join(f'<li><a href="{esc(x["url"])}">{esc(x["title"])}</a></li>' for x in data['news'][:10])+'</ul>'
    index=index.replace('__NOSCRIPT__',fallback).replace('assets/app.js','assets/app.js?v='+asset_version('app.js')).replace('assets/style.css','assets/style.css?v='+asset_version('style.css'))
    (out/'index.html').write_text(index)
    (out/'.nojekyll').touch()
    (out/'policies.html').write_text(page('Sources & policy',POLICIES))
    health=load(ROOT/'data/health.json',{});counts=data['counts']
    stats=''.join(f'<div class="status-stat"><strong>{esc(v)}</strong>{esc(k)}</div>' for k,v in [('News / חדשות',counts['news']),('Videos / וידאו',counts['videos']),('Working feeds / עדכונים פעילים',counts['active_sources'])])
    rows=''.join(f'<li><strong>{esc(s["id"])}</strong>: {esc(s["state"])}'+(f' · {esc(s.get("error", ""))}' if s.get('error') else '')+'</li>' for s in data['source_status'])
    (out/'status.html').write_text(page('Publication status',f'<h1>Publication status<br>מצב הפרסום</h1><p>Latest completed collection / האיסוף האחרון: {esc(data["generated_at"])}</p><div class="status-grid">{stats}</div><p>Automatic source collection is not human editorial review. / איסוף אוטומטי אינו בדיקה של עורך אנושי.</p><ul>{rows}</ul><p><a href="https://github.com/Moriahise/Moriah/actions">Workflow history / היסטוריית ההרצות</a></p>'))
    arts=out/'articles';arts.mkdir()
    for a in data['features']:
        for lang in ('en','he'):
            alternate='he' if lang=='en' else 'en'
            body=f'<p><a href="{a["id"]}.{alternate}.html">{alternate.upper()}</a></p>'+feature_body(a,lang)
            (arts/f'{a["id"]}.{lang}.html').write_text(page(a['title'][lang],body,lang,prefix='../'))
    cache=ROOT/'.pdf-cache';cache.mkdir(exist_ok=True)
    issues=load(ROOT/'data/issues.json',[])
    for i in issues:
        issue=load(ROOT/'data/issues'/f'{i["id"]}.json');folder=out/'editions'/i['id'];folder.mkdir(parents=True)
        for lang in ('en','he'):
            text=make_issue(issue,lang);(folder/f'{lang}.html').write_text(text)
            filename=f'MORIAH-{i["id"]}-{lang}.pdf'
            key=__import__('hashlib').sha256((text+'pdf-layout-v1').encode()).hexdigest()[:20]
            cached=cache/(key+'.pdf')
            if pdfs:
                if not cached.exists():
                    from weasyprint import HTML
                    HTML(string=text,base_url=str(folder)).write_pdf(cached)
                shutil.copyfile(cached,folder/filename)
    settings=load(ROOT/'config/settings.json');base=settings['base_url']
    feed='<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>MORIAH | מוריה</title><link>'+xml_escape(base)+'</link><description>Publisher-attributed source links. Translations are machine-generated.</description>'
    for x in data['news'][:40]:
        feed+='<item><title>'+xml_escape(x['title'])+'</title><link>'+xml_escape(x['url'])+'</link><guid isPermaLink="false">'+x['id']+'</guid><description>'+xml_escape(source_names(data,'en').get(x['source_id'],x['source_id']))+'</description></item>'
    (out/'feed.xml').write_text(feed+'</channel></rss>')
    urls=['index.html','policies.html','status.html']+[f'articles/{a["id"]}.{lang}.html' for a in data['features'] for lang in ('en','he')]
    (out/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+xml_escape(base+u)+'</loc></url>' for u in urls)+'</urlset>')
    (out/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+base+'sitemap.xml\n')
    # Keep the repository's front-page HTML in sync; deploy the complete _site artifact.
    shutil.copyfile(out/'index.html',ROOT/'index.html')
    print(f'Built {len(data["news"])} headlines, {len(data["features"])} bilingual guides, {len(issues)} archived issues into {out}')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default=str(ROOT/'_site'));p.add_argument('--no-pdf',action='store_true');a=p.parse_args();build(Path(a.output).resolve(),not a.no_pdf)
