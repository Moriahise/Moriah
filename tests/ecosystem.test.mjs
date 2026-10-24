import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {HDate,DEFAULT_CITY,civilDate,weekTarget,calcDaf,weeklyRecord,weeklyStudy,findHaftarah,allParashot,hebrewToday,monthModel,monthStep,dayTimes,rotate,qaSelection,citySpec} from '../src/ecosystem-core.mjs';
const data=JSON.parse(fs.readFileSync(new URL('../data/ecosystem.json',import.meta.url)));
const news=JSON.parse(fs.readFileSync(new URL('../data/latest.json',import.meta.url)));
test('weekly study follows the source Wednesday rollover through Sunday and Tuesday',()=>{
 for(const [d,target] of [['2026-10-24','2026-10-24'],['2026-10-25','2026-10-24'],['2026-10-27','2026-10-24'],['2026-10-28','2026-10-31']])assert.equal(weekTarget(d),target);
});
test('Israel civil midnight drives Daf independently of browser timezone',()=>{
 assert.equal(civilDate(new Date('2026-10-24T20:59:59Z')),'2026-10-24');
 assert.equal(civilDate(new Date('2026-10-24T21:00:00Z')),'2026-10-25');
 const d=calcDaf('2026-10-24',data.daf.calendar);assert.equal(d.id,'cycle-14-bekhorot-36');assert.ok(data.daf.editions.some(e=>e.id===d.id));
 assert.equal(calcDaf('1975-06-24',data.daf.calendar).id,'cycle-8-berakhot-2');
 assert.throws(()=>calcDaf('1975-06-23',data.daf.calendar));
});
test('weekly links match published source IDs and avoid combined Haftarah collisions',()=>{
 const w=weeklyRecord(data,'2026-10-24',true);assert.equal(w.reading.he,'לך לך');
 assert.match(weeklyStudy(data.shiurim,w.target_shabbat,w.reading).url,/Shiurim\/shiur\/5787-2026-10-24\/$/);
 assert.match(findHaftarah(data,w).url,/haftarah-lech-lecha\/$/);
 const fixture={shiurim:{haftarot:[{title:{en:'Haftarah · Achrei Mot-Kedoshim'},url:'combined'},{title:{en:'Haftarah · Achrei Mot'},url:'single'}]}};
 assert.equal(findHaftarah(fixture,{reading:{en:'Achrei Mot'}}).url,'single');
 assert.equal(weeklyStudy(data.shiurim,w.target_shabbat,{he:'נח'}),null);
});
test('all 54 portions are visible and unpublished Zohar studies are not invented',()=>{
 const rows=allParashot(data.zohar);assert.equal(rows.length,54);assert.equal(rows.filter(r=>r.edition).length,3);
 assert.equal(rows.find(r=>r.en==='Lech-Lecha').edition.id,'5787-2026-10-24');assert.equal(rows.at(-1).edition,null);
});
test('Hebrew date changes at local sunset and leap-month navigation crosses Adar correctly',()=>{
 const before=hebrewToday(DEFAULT_CITY,new Date('2026-10-24T12:00:00Z')),after=hebrewToday(DEFAULT_CITY,new Date('2026-10-24T18:00:00Z'));assert.equal(after.abs(),before.abs()+1);
 assert.deepEqual(monthStep('hebrew',5787,12,1),{year:5787,month:13});assert.deepEqual(monthStep('hebrew',5787,13,1),{year:5787,month:1});
 assert.deepEqual(monthStep('hebrew',5787,6,1),{year:5788,month:7});
});
test('month calendar includes local candle lighting, readings and eight ordered daily times',()=>{
 const city=citySpec(news,'vienna'),month=monthModel('civil',2026,10,city);assert.equal(month.days.length,31);
 const friday=month.days.find(d=>d.civil==='2026-10-23');assert.ok(friday.events.some(e=>e.getDesc()==='Candle lighting'&&e.eventTime instanceof Date));
 assert.ok(month.days.find(d=>d.civil==='2026-10-24').events.some(e=>e.getCategories().includes('parashat')));
 const times=dayTimes('2026-10-24',city);assert.equal(times.length,8);assert.ok(times.at(0).value<times.at(-1).value);
});
test('music playlists refer to real tracks across all nine collections',()=>{
 assert.equal(data.music.length,9);assert.ok(data.music.reduce((n,c)=>n+c.tracks.length,0)>600);
 for(const c of data.music){const ids=new Set(c.tracks.map(t=>t.id));for(const p of [...c.playlists,...c.series])assert.ok(p.items.every(id=>ids.has(id)));for(const t of c.tracks){if(t.youtube_id)assert.match(t.youtube_id,/^[A-Za-z0-9_-]{11}$/);assert.ok(t.page_url.startsWith(c.url));}}
 assert.notDeepEqual(rotate(data.music,0),rotate(data.music,1));
});
test('question rotation uses answered native-language records with actual reader deep links',()=>{
 for(const lang of ['he','en']){const cards=qaSelection(data.qa.cards,lang,1,3);assert.equal(cards.length,3);assert.ok(cards.every(q=>q.language===lang&&q.answer_count>0&&q.url.startsWith('https://shekhina.org/qa.html?id=')));assert.notDeepEqual(cards,qaSelection(data.qa.cards,lang,4,3));}
});
