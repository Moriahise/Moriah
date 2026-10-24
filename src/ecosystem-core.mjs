import {HDate,GeoLocation,Location,Zmanim,calendar,ParshaEvent,parshiot,Locale,gematriya} from '@hebcal/core';
export {HDate,parshiot,Locale,gematriya};
export const normalize=s=>String(s||'').normalize('NFKD').replace(/[\u0591-\u05c7״׳'’"\s-]/g,'').toLowerCase();
export function civilDate(now=new Date(),tz='Asia/Jerusalem'){
 const p=Object.fromEntries(new Intl.DateTimeFormat('en-US',{timeZone:tz,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now).map(x=>[x.type,x.value]));return `${p.year}-${p.month}-${p.day}`;
}
export function weekTarget(day){const d=new Date(day+'T12:00:00Z'),w=d.getUTCDay();d.setUTCDate(d.getUTCDate()+(w>=3?6-w:-(w+1)));return d.toISOString().slice(0,10);}
export function dayOrdinal(day){return Math.floor(Date.parse(day+'T00:00:00Z')/86400000);}
export function rotate(items,seed,count=1){if(!items?.length)return [];const start=((seed%items.length)+items.length)%items.length;return Array.from({length:Math.min(count,items.length)},(_,i)=>items[(start+i)%items.length]);}
export function weeklyStudy(section,target,reading=null){return section?.editions?.filter(e=>e.target_shabbat===target&&(!reading||normalize(e.parashah?.he)===normalize(reading.he))).at(0)||null;}
export function weeklyRecord(ecosystem,target,il=true){const week=ecosystem?.shiurim?.weeks?.find(w=>w.target_shabbat===target)||ecosystem?.zohar?.weeks?.find(w=>w.target_shabbat===target);return week?{...week,il,reading:il?week.israel:week.diaspora}:null;}
export function findHaftarah(ecosystem,week){
 if(!week?.reading)return null;
 const clean=s=>normalize(String(s||'').replace(/^Haftarah\s*[·:–-]?\s*/i,'').replace(/^הפטרה\s*[·:–-]?\s*/,''));
 const he=clean(week.reading.he),en=clean(week.reading.en),all=ecosystem?.shiurim?.haftarot||[];
 if(week.target_shabbat){
  const h=plainHDate(week.target_shabbat),next=h.add(1,'day');
  const events=calendar({start:h.greg(),end:next.greg(),il:week.il!==false,sedrot:true});
  const names=events.filter(e=>e.getDate().abs()===h.abs()).map(e=>e.getDesc());
  const has=name=>names.includes(name),rosh=h.getDate()===1||h.getDate()===30;
  const special=[];
  if(has('Shabbat Shekalim'))special.push(rosh?'shabbat-shekalim-on-rosh-chodesh':'shabbat-shekalim');
  if(has('Shabbat Zachor'))special.push('shabbat-zachor');
  if(has('Shabbat Parah'))special.push('shabbat-parah');
  if(has('Shabbat HaChodesh'))special.push(rosh?'shabbat-hachodesh-on-rosh-chodesh':'shabbat-hachodesh');
  if(has('Shabbat HaGadol'))special.push('shabbat-hagadol');
  if(has('Shabbat Shuva'))special.push(en===clean('Haazinu')?'shabbat-shuva-with-ha-azinu':en===clean('Vayeilech')?'shabbat-shuva-with-vayeilech':'shabbat-shuva');
  if(names.some(n=>n.startsWith('Chanukah:')))special.push(rosh?'shabbat-rosh-chodesh-chanukah':'chanukah-first-shabbat');
  for(const n of names){
   if(/^Pesach .*CH/.test(n))special.push('pesach-shabbat-chol-ha-moed');
   if(/^Sukkot .*CH/.test(n))special.push('sukkot-shabbat-chol-ha-moed');
   const fixed={'Rosh Hashana I':'rosh-hashana-i','Rosh Hashana II':'rosh-hashana-ii','Yom Kippur':'yom-kippur','Sukkot I':'sukkot-i','Sukkot II':'sukkot-ii','Shmini Atzeret':'shmini-atzeret','Simchat Torah':'simchat-torah','Pesach I':'pesach-i','Pesach II':'pesach-ii','Pesach VII':'pesach-vii','Pesach VIII':'pesach-viii','Shavuot':'shavuot','Shavuot I':'shavuot-i','Shavuot II':'shavuot-ii'};
   if(fixed[n])special.push(fixed[n]);
  }
  if(rosh)special.push(en===clean('Masei')?'masei-on-shabbat-rosh-chodesh':'shabbat-rosh-chodesh');
  else if(next.getDate()===1||next.getDate()===30)special.push('shabbat-machar-chodesh');
  if(h.getMonth()===4&&h.getDate()>17&&en===clean('Pinchas'))special.push('pinchas-occurring-after-17-tammuz');
  for(const id of special){const found=all.find(x=>x.id==='haftarah-'+id);if(found)return found;}
 }

 // Exact names prevent single portions from selecting a combined-reading study.
 return all.find(h=>he&&clean(h.title?.he)===he)||all.find(h=>en&&clean(h.title?.en)===en)||null;
}
export function calcDaf(day,calendarData){
 const elapsed=dayOrdinal(day)-dayOrdinal('1975-06-24');if(!Number.isFinite(elapsed)||elapsed<0)throw new Error('Daf Yomi date is outside the supported range');
 let rest=elapsed%2711;const cycle=8+Math.floor(elapsed/2711);
 for(const tractate of calendarData?.tractates||[]){if(rest<tractate.days){const daf=tractate.first_daf+rest;return {id:`cycle-${cycle}-${tractate.id}-${daf}`,cycle,daf,date:day,tractate,title:{en:`${tractate.en} ${daf}`,he:`${tractate.he} דף ${daf}`}};}rest-=tractate.days;}
 throw new Error('Daf Yomi calendar unavailable');
}
export const DEFAULT_CITY={latitude:31.76904,longitude:35.21633,tzid:'Asia/Jerusalem',city:'Jerusalem',israel:true,candle_minutes:40};
export function citySpec(payload,id){const c=payload?.calendars?.[id];if(!c)return {...DEFAULT_CITY};const l=c.data.location;return {latitude:l.latitude,longitude:l.longitude,tzid:l.tzid,city:l.city||l.title,israel:c.city.israel,candle_minutes:c.method.candle_minutes};}
export function geo(city){return new GeoLocation(city.city,city.latitude,city.longitude,0,city.tzid);}
export function hebrewToday(city,now=new Date()){return Zmanim.makeSunsetAwareHDate(geo(city),now,false);}
export function plainHDate(day){const [y,m,d]=day.split('-').map(Number);return new HDate(new Date(y,m-1,d,12));}
export function isoHDate(h){const d=h.greg();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
const eventCache=new Map();
export function yearEvents(year,city){
 const key=[year,city.israel,city.latitude,city.longitude,city.tzid,city.candle_minutes].join('|');
 if(!eventCache.has(key)){
  const location=new Location(city.latitude,city.longitude,city.israel,city.tzid,city.city,city.israel?'IL':undefined);
  const events=calendar({year,isHebrewYear:true,il:city.israel,sedrot:true,omer:true,candlelighting:true,location,candleLightingMins:city.candle_minutes,havdalahDeg:8.5,useElevation:false});
  eventCache.set(key,events);if(eventCache.size>48)eventCache.delete(eventCache.keys().next().value);
 }
 return eventCache.get(key);
}
export function monthModel(system,year,month,city){
 let days=[];
 if(system==='hebrew'){const first=new HDate(1,month,year);days=Array.from({length:first.daysInMonth()},(_,i)=>new HDate(i+1,month,year));}
 else {const count=new Date(year,month,0,12).getDate();days=Array.from({length:count},(_,i)=>new HDate(new Date(year,month-1,i+1,12)));}
 const events=[...new Set(days.map(h=>h.getFullYear()))].flatMap(y=>yearEvents(y,city));const byDate=new Map();
 for(const e of events){const n=e.getDate().abs();if(!byDate.has(n))byDate.set(n,[]);byDate.get(n).push(e);}
 return {offset:days[0].getDay(),days:days.map(h=>({h,civil:isoHDate(h),events:byDate.get(h.abs())||[]}))};
}
export function monthStep(system,year,month,delta){if(system==='hebrew'){const h=new HDate(1,month,year).add(delta,'month');return {year:h.getFullYear(),month:h.getMonth()};}const d=new Date(year,month-1+delta,1,12);return {year:d.getFullYear(),month:d.getMonth()+1};}
export function dayTimes(day,city){const [y,m,d]=day.split('-').map(Number);const z=new Zmanim(geo(city),new Date(y,m-1,d,12),false);const defs=[['dawn','alotHaShachar'],['sunrise','sunrise'],['shema','sofZmanShma'],['prayer','sofZmanTfilla'],['midday','chatzot'],['mincha','minchaGedola'],['sunset','sunset']];const out=defs.flatMap(([key,method])=>{const value=z[method]?.();return value instanceof Date&&!Number.isNaN(value.getTime())?[{key,value}]:[];});const night=z.tzeit(8.5);if(night&&!Number.isNaN(night.getTime()))out.push({key:'nightfall',value:night});return out;}
export function allParashot(section){return parshiot.map((en,index)=>{const he=Locale.gettext(en,'he');const editions=section?.editions?.filter(e=>normalize(e.parashah?.he)===normalize(he))||[];return {index,en,he,edition:editions.sort((a,b)=>b.target_shabbat.localeCompare(a.target_shabbat))[0]||null};});}
export function qaSelection(cards,lang,seed,count=3){const native=cards.filter(q=>q.language===lang),other=cards.filter(q=>q.language!==lang);return rotate(native.length?native:other,seed,count);}
