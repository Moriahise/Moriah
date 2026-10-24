import {HDate,Locale,gematriya,normalize,civilDate,weekTarget,dayOrdinal,rotate,weeklyStudy,weeklyRecord,findHaftarah,calcDaf,citySpec,hebrewToday,plainHDate,isoHDate,monthModel,monthStep,dayTimes,allParashot,qaSelection} from './ecosystem-core.mjs';
const $=id=>document.getElementById(id);
const S={data:null,eco:null,lang:'en',city:'jerusalem',system:'hebrew',cursor:null,selected:null,musicOffset:0,collection:null,playing:false,queue:[],queueIndex:0,dafDate:null,dafManual:false,qaOffset:0,lastDay:null,zoharQuery:''};
const T=(en,he)=>S.lang==='he'?he:en;
function el(tag,attrs={},...children){const n=document.createElement(tag);for(const [k,v] of Object.entries(attrs)){if(k==='class')n.className=v;else if(k.startsWith('on'))n.addEventListener(k.slice(2),v);else n.setAttribute(k,String(v));}for(const c of children.flat())if(c!==null&&c!==undefined)n.append(c.nodeType?c:document.createTextNode(String(c)));return n;}
function put(id,...children){$(id)?.replaceChildren(...children.flat());}
function a(url,label,cls='text-link'){let safe='#';try{const u=new URL(url);if(u.protocol==='https:')safe=u.href;}catch{}return el('a',{href:safe,target:'_blank',rel:'noopener noreferrer',class:cls},label);}
function button(label,fn,attrs={}){return el('button',{type:'button',onclick:fn,...attrs},label);}
function title(o){return o?.[S.lang]||o?.en||o?.he||'';}
function getWeek(target=weekTarget(civilDate())){return weeklyRecord(S.eco,target,citySpec(S.data,S.city).israel);}
function contextualLesson(section,target){return weeklyStudy(section,target,getWeek(target)?.reading);}
function weeklyLinks(){
 const target=weekTarget(civilDate()),week=getWeek(target),study=contextualLesson(S.eco?.shiurim,target),haftarah=findHaftarah(S.eco,week);
 const parashaUrl=study?.url||S.eco?.links?.shiurim||'https://moriahise.github.io/Shiurim/';
 const parashaName=week?title(week.reading):$('parashah-name')?.textContent||T('Weekly parashah','פרשת השבוע');
 put('parashah-name',a(parashaUrl,parashaName,'reading-link'));
 const href=haftarah?.url||'https://moriahise.github.io/Shiurim/haftarot/';
 const label=haftarah?title(haftarah.title):$('haftarah-name')?.textContent||T('Haftarah study','לימוד ההפטרה');
 put('haftarah-name',a(href,label,'reading-link'));
 put('weekly-reading-date',T('Study for Shabbat · ','לימוד לשבת · ')+target);
 const cards=[];
 cards.push(el('article',{class:'daily-card'},el('span',{class:'eyebrow gold'},T('PARASHAH & HAFTARAH','פרשה והפטרה')),el('h3',{},a(parashaUrl,parashaName,'')),el('p',{},study?title(study.title):T('Explore the current weekly study.','לימוד השבוע מתוך ספריית השיעורים.')),a(href,T('Read the Haftarah →','לקריאת ההפטרה ←')),el('small',{},target)));
 const day=civilDate();let row;try{row=calcDaf(day,S.eco?.daf?.calendar);}catch{}
 const dStudy=row?S.eco?.daf?.editions?.find(e=>e.id===row.id):null;const dURL=dStudy?.url||'https://moriahise.github.io/Daf-Yomi/?date='+day;
 cards.push(el('article',{class:'daily-card daf-feature'},el('span',{class:'eyebrow gold'},T('TODAY’S DAF YOMI','הדף היומי')),el('h3',{},a(dURL,row?title(row.title):T('Daily Talmud study','לימוד יומי בתלמוד'),'')),el('p',{},dStudy?title(dStudy.title):T('The day’s daf, with a direct route to the Daf Yomi reader.','הדף של היום, עם מעבר ישיר ללימוד הדף היומי.')),a(dURL,T('Open today’s daf →','ללימוד הדף היומי ←')),el('small',{},day+' · '+T('Israel date','תאריך ישראל'))));
 const zStudy=contextualLesson(S.eco?.zohar,target);const zurl=zStudy?.url||'https://moriahise.github.io/Zohar/';
 cards.push(el('article',{class:'daily-card'},el('span',{class:'eyebrow gold'},T('ZOHAR OF THE WEEK','זוהר השבוע')),el('h3',{},a(zurl,parashaName,'')),el('p',{},zStudy?title(zStudy.title):T('The weekly reading is shown in the programme below; a study link appears when published.','הפרשה מופיעה בתוכנית להלן; קישור ללימוד יופיע לאחר פרסומו.')),el('a',{href:'#zohar',class:'text-link'},T('All 54 readings below','כל 54 הפרשות בהמשך'))));
 
 put('daily-cards',cards);
 // Replace the former third-party Daf link with the owner’s actual daily reader.
 put('daf-line',a(dURL,(row?title(row.title):T('Daf Yomi','הדף היומי'))+' · '+day));
}
function calendarClock(){
 const now=new Date(),city=citySpec(S.data,S.city),hd=hebrewToday(city,now),j=hebrewToday(citySpec(S.data,'jerusalem'),now);
 put('calendar-today',el('strong',{},S.lang==='he'?j.renderGematriya():j.toString()),el('span',{},new Intl.DateTimeFormat(S.lang==='he'?'he-IL':'en-GB',{timeZone:'Asia/Jerusalem',dateStyle:'full'}).format(now)),el('span',{class:'calendar-clock'},T('Israel time · ','שעון ישראל · ')+new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Jerusalem',hour:'2-digit',minute:'2-digit'}).format(now)));
 put('calendar-local-date',T('Selected city: ','העיר הנבחרת: ')+city.city+' · '+(S.lang==='he'?hd.renderGematriya():hd.toString())+' · '+city.tzid);
 return hd;
}
function renderMonth(){
 if(!$('calendar-grid'))return;
 const city=citySpec(S.data,S.city),today=calendarClock(),civil=civilDate(new Date(),city.tzid);
 if(!S.cursor)S.cursor=S.system==='hebrew'?{year:today.getFullYear(),month:today.getMonth()}:{year:+civil.slice(0,4),month:+civil.slice(5,7)};
 if(!S.selected)S.selected=isoHDate(today);
 S.lastHebAbs=today.abs();const {year,month}=S.cursor,model=monthModel(S.system,year,month,city);
 const head=S.system==='hebrew'?(S.lang==='he'?Locale.gettext(new HDate(1,month,year).getMonthName(),'he')+' '+gematriya(year):new HDate(1,month,year).getMonthName()+' '+year):new Intl.DateTimeFormat(S.lang==='he'?'he-IL':'en-GB',{month:'long',year:'numeric'}).format(new Date(year,month-1,1,12));
 put('calendar-month-title',head);
 put('calendar-mode',button(T('Hebrew month','חודש עברי'),()=>changeSystem('hebrew'),{'aria-pressed':S.system==='hebrew'}),button(T('Civil month','חודש לועזי'),()=>changeSystem('civil'),{'aria-pressed':S.system==='civil'}));
 put('calendar-actions',button(T('← Previous month','החודש הקודם ←'),()=>{S.monthManual=true;S.cursor=monthStep(S.system,year,month,-1);renderMonth();},{'aria-label':T('Previous month','החודש הקודם')}),button(T('Today','היום'),()=>{S.monthManual=false;S.cursor=null;S.selected=isoHDate(hebrewToday(city));renderMonth();}),button(T('Next month →','→ החודש הבא'),()=>{S.monthManual=true;S.cursor=monthStep(S.system,year,month,1);renderMonth();},{'aria-label':T('Next month','החודש הבא')}));
 const days=S.lang==='he'?['א׳','ב׳','ג׳','ד׳','ה׳','ו׳','שבת']:['Sun','Mon','Tue','Wed','Thu','Fri','Shabbat'];
 put('calendar-weekdays',...days.map(d=>el('div',{role:'columnheader'},d)));
 const nodes=Array.from({length:model.offset},()=>el('div',{class:'calendar-blank','aria-hidden':'true'}));
 for(const day of model.days){
  const current=S.system==='hebrew'?day.h.abs()===today.abs():day.civil===civil;const selected=day.civil===S.selected;
  const label=S.lang==='he'?day.h.renderGematriya():day.h.toString();
  const events=day.events.filter(e=>!e.getCategories().includes('candles')&&!e.getCategories().includes('havdalah'));
  const b=button('',()=>{S.selected=day.civil;renderMonth();},{class:'calendar-day'+(current?' is-today':'')+(selected?' is-selected':'')+(day.h.getDay()===6?' is-shabbat':''),'aria-label':label+' · '+day.civil,'aria-pressed':selected});
  b.append(el('span',{class:'calendar-hebrew-number'},S.lang==='he'?gematriya(day.h.getDate()):day.h.getDate()),el('span',{class:'calendar-civil-number'},day.civil.slice(8)+' '+new Intl.DateTimeFormat(S.lang==='he'?'he-IL':'en-GB',{month:'short'}).format(day.h.greg())));
  for(const e of events.slice(0,2))b.append(el('span',{class:'calendar-event'},e.render(S.lang==='he'?'he':'en')));
  if(events.length>2)b.append(el('span',{class:'calendar-extra'},'+'+(events.length-2)));
  nodes.push(b);
 }
 put('calendar-grid',nodes);
 const picked=model.days.find(d=>d.civil===S.selected);if(picked)renderDay(picked,city);else put('calendar-selected',T('Choose a date to view events and daily times.','בחרו תאריך להצגת אירועים וזמני היום.'));
}
function changeSystem(system){S.system=system;S.cursor=null;renderMonth();}
function renderDay(day,city){
 const labels={dawn:T('Dawn · 16.1°','עלות השחר · 16.1°'),sunrise:T('Sunrise','הנץ החמה'),shema:T('Latest Shema · GRA','סוף זמן שמע · גר״א'),prayer:T('Latest Shacharit · GRA','סוף זמן תפילה · גר״א'),midday:T('Solar noon','חצות היום'),mincha:T('Mincha Gedolah','מנחה גדולה'),sunset:T('Sunset','שקיעה'),nightfall:T('Nightfall · 8.5°','צאת הכוכבים · 8.5°')};
 const fmt=new Intl.DateTimeFormat('en-GB',{timeZone:city.tzid,hour:'2-digit',minute:'2-digit'});
 const events=day.events.map(e=>{const text=e.render(S.lang==='he'?'he':'en');const isReading=e.getCategories().includes('parashat');const study=isReading?contextualLesson(S.eco?.shiurim,day.civil):null;return el('li',{},study?a(study.url,text,''):text);});
 const times=dayTimes(day.civil,city).map(x=>el('div',{class:'zman-row'},el('span',{},labels[x.key]),el('time',{datetime:x.value.toISOString()},fmt.format(x.value))));
 for(const e of day.events){if(e.eventTime instanceof Date)times.push(el('div',{class:'zman-row'},el('span',{},e.render(S.lang==='he'?'he':'en').replace(/:.*$/,'')),el('time',{datetime:e.eventTime.toISOString()},fmt.format(e.eventTime))));}
 put('calendar-selected',el('h3',{},S.lang==='he'?day.h.renderGematriya():day.h.toString()),el('p',{class:'small'},day.civil+' · '+city.city+' · '+city.tzid),events.length?el('ul',{class:'calendar-event-list'},events):el('p',{class:'small'},T('No special observance on this date.','אין אירוע מיוחד בתאריך זה.')),el('div',{class:'zmanim-list'},times),el('p',{class:'small'},T('Calculated at sea level. Candle lighting: ','חישוב בגובה פני הים. הדלקת נרות: ')+city.candle_minutes+T(' min before sunset; Havdalah 8.5°.',' דקות לפני השקיעה; הבדלה 8.5°.')));
}
function renderDaf(){
 const today=civilDate();if(!S.dafManual)S.dafDate=today;
 let row;try{row=calcDaf(S.dafDate,S.eco?.daf?.calendar);}catch{put('daf-current',a('https://moriahise.github.io/Daf-Yomi/',T('Open Daf Yomi','לספריית הדף היומי')));return;}
 const study=S.eco.daf.editions.find(e=>e.id===row.id),url=study?.url||'https://moriahise.github.io/Daf-Yomi/?date='+row.date;
 const input=el('input',{type:'date',value:S.dafDate,min:'1975-06-24','aria-label':T('Daf Yomi date','תאריך הדף היומי'),onchange:e=>{if(!/^\d{4}-\d{2}-\d{2}$/.test(e.target.value))return;S.dafDate=e.target.value;S.dafManual=true;renderDaf();weeklyLinks();}});
 const move=delta=>{const d=new Date(S.dafDate+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+delta);S.dafDate=d.toISOString().slice(0,10);S.dafManual=true;renderDaf();weeklyLinks();};
 put('daf-current',el('div',{class:'daf-title-block'},el('span',{class:'eyebrow gold'},T('DAILY · DATE IN ISRAEL','יומי · לפי תאריך ישראל')),el('h3',{},a(url,title(row.title),'')),el('p',{},study?title(study.title):T('Open the reader for this date.','פתחו את הלימוד לתאריך הנבחר.')),el('p',{class:'small'},row.date+' · '+T('Cycle ','מחזור ')+row.cycle)),el('div',{class:'daf-date-controls'},button(T('← Previous daf','הדף הקודם ←'),()=>move(-1)),input,button(T('Next daf →','→ הדף הבא'),()=>move(1)),button(T('Today','היום'),()=>{S.dafManual=false;renderDaf();weeklyLinks();})),a(url,T('Read the full daily study →','לקריאת השיעור היומי המלא ←'),'primary-link'));
}
function renderMusic(){
 const all=S.eco?.music||[],usable=all.filter(c=>c.tracks?.length);if(!usable.length){put('music-feature',a('https://shekhina.org/index.html#songs',T('Explore the song collections','לספריית השירים והניגונים')));return;}
 const seed=dayOrdinal(civilDate())+S.musicOffset;const c=usable.find(x=>x.id===S.collection)||rotate(usable,seed)[0];
 const playlists=c.playlists||[];const pl=rotate(playlists,Math.floor(seed/Math.max(1,usable.length)))[0];const series=rotate(c.series||[],seed)[0];
 const entries=pl?pl.items.map(id=>c.tracks.find(t=>t.id===id)).filter(Boolean):rotate(c.tracks,seed,8);
 const track=rotate(c.tracks,seed)[0];
 put('music-feature',el('div',{class:'music-emblem','aria-hidden':'true'},'♪'),el('div',{},el('span',{class:'eyebrow gold'},T('THE ROTATING COLLECTION','האוסף המתחלף')),el('h3',{},a(c.url,title(c.title),'')),el('p',{},title(c.description)),el('div',{class:'music-actions'},button(T('Play the playlist','נגנו את הפלייליסט'),()=>playQueue(entries,0),{class:'primary-link'}),a(c.url,T('Open the collection ↗','לפתיחת האוסף ↖')),el('p',{class:'small'},c.tracks.length+' '+T('tracks in the source collection','קטעים באוסף המקור')))));
 put('music-rotation',button(T('← Previous collection','האוסף הקודם ←'),()=>{S.collection=null;S.musicOffset--;renderMusic();},{'aria-label':T('Previous music collection','אוסף הניגונים הקודם')}),button(T('Next collection →','→ האוסף הבא'),()=>{S.collection=null;S.musicOffset++;renderMusic();},{'aria-label':T('Next music collection','אוסף הניגונים הבא')}));
 put('music-playlist-title',pl?T('Playlist · ','פלייליסט · ')+title(pl.title):T('A playlist from the collection','פלייליסט מתוך האוסף'));
 put('music-playlist',...entries.slice(0,12).map((t,i)=>el('li',{},button(title(t.title),()=>playQueue(entries,i),{class:'track-button',dir:'auto'}),t.maqam?el('small',{},t.maqam):null,a(t.page_url,T('Lyrics ↗','מילים ↖'),'small-link'))));
 const seriesTracks=series?series.items.map(id=>c.tracks.find(t=>t.id===id)).filter(Boolean):[];
 put('music-series',el('span',{class:'eyebrow gold'},T('A SERIES TO FOLLOW','סדרה להמשך')),el('h3',{dir:'auto'},series?.title||title(c.title)),el('p',{},T('Follow the related pieces in their collection order.','עקבו אחר קטעי הסדרה לפי סדרם באוסף.')),seriesTracks.length?button(T('Play the series →','לנגינת הסדרה ←'),()=>playQueue(seriesTracks,0),{class:'outline-button'}):a(c.url,T('Open the series','לפתיחת הסדרה')));
 put('music-collections',...all.map(col=>button(title(col.title),()=>{S.collection=col.id;renderMusic();},{class:'collection-chip','aria-pressed':c.id===col.id})));
 if(!$('music-player').childNodes.length)put('music-player',el('p',{class:'small'},T('Choose a track or playlist to start. Sound never starts automatically.','בחרו קטע או פלייליסט להפעלה. הצליל אינו מתחיל ללא בחירה.')));
}
function playQueue(queue,index){
 S.queue=queue;S.queueIndex=index;S.playing=true;const song=queue[index];if(!song)return;
 let media;
 if(song.youtube_id){const rest=queue.slice(index+1).filter(t=>t.youtube_id).map(t=>t.youtube_id);media=el('iframe',{src:'https://www.youtube-nocookie.com/embed/'+song.youtube_id+'?autoplay=1'+(rest.length?'&playlist='+rest.join(','):''),class:'music-iframe',title:title(song.title),allow:'autoplay; encrypted-media; picture-in-picture',allowfullscreen:'',referrerpolicy:'strict-origin-when-cross-origin'});}
 else if(song.audio_url){media=el('audio',{controls:'',autoplay:'',src:song.audio_url,preload:'none'});media.addEventListener('ended',()=>{if(index+1<queue.length)playQueue(queue,index+1);else S.playing=false;});media.addEventListener('error',()=>{put('music-playback-note',T('This recording is unavailable here. Open the original collection.','ההקלטה אינה זמינה כאן. פתחו את אוסף המקור.'));});}
 else {S.playing=false;media=a(song.page_url,T('Open this song in its collection','לפתיחת השיר באוסף המקור'));}
 put('music-player',el('h3',{dir:'auto'},title(song.title)),media,el('div',{class:'music-actions'},button(T('Previous track','הקטע הקודם'),()=>playQueue(queue,(index-1+queue.length)%queue.length)),button(T('Next track','הקטע הבא'),()=>playQueue(queue,(index+1)%queue.length)),button(T('Stop playback','עצירת הנגינה'),()=>{S.playing=false;put('music-player',el('p',{class:'small'},T('Playback stopped.','הנגינה נעצרה.')));}),a(song.page_url,T('Read the song ↗','לקריאת השיר ↖'))),el('p',{id:'music-playback-note',class:'small'},T('Playback is supplied by the original collection or YouTube. The collection continues to rotate when playback is stopped.','הנגינה מסופקת מאוסף המקור או מיוטיוב. האוסף מתחלף כאשר הנגינה עצורה.')));
}
function renderQA(){
 const cards=S.eco?.qa?.cards||[],selected=qaSelection(cards,S.lang,dayOrdinal(civilDate())+S.qaOffset,3);
 put('qa-cards',...selected.map(q=>{const n=el('article',{class:'qa-card',dir:'auto'},el('span',{class:'eyebrow gold'},q.provider+' · '+q.answer_count+' '+T('answers','תשובות')),el('h3',{},a(q.url,q.titles?.[S.lang]||q.title,'')),el('p',{class:'question-preview'},q.question),q.answer?el('blockquote',{},q.answer+'…'):el('p',{class:'small'},T('The full answer is available in the Sanhedrin reader.','התשובה המלאה זמינה בספריית סנהדרין.')),a(q.url,T('Read question & full answer →','לשאלה ולתשובה המלאה ←')),el('p',{class:'qa-credit'},q.author?`${q.author} · `:'',q.license||T('Source attribution','ייחוס למקור'),q.source_url?a(q.source_url,T('Original source','מקור'),'small-link'):null));return n;}));
 if(!selected.length)put('qa-cards',a('https://shekhina.org/index.html',T('Open the Q&A library','לספריית השאלות והתשובות')));
 put('qa-actions',button(T('More questions →','שאלות נוספות ←'),()=>{S.qaOffset+=3;renderQA();},{class:'outline-button'}),a('https://shekhina.org/index.html',T('Search all questions ↗','לחיפוש בכל השאלות ↖')));
}
function renderZohar(){
 const target=weekTarget(civilDate()),week=getWeek(target),study=contextualLesson(S.eco?.zohar,target),preview=S.eco?.zohar?.preview;
 put('zohar-current',el('span',{class:'eyebrow gold'},T('THIS WEEK · ','השבוע · ')+target),el('h3',{},week?title(week.reading):T('Weekly Zohar','זוהר השבוע')),el('p',{class:'zohar-deck'},study?title(study.title):T('The weekly programme continues. A direct study link is shown when the corresponding lesson is published.','תוכנית הלימוד נמשכת. קישור ישיר יוצג כאשר יתפרסם השיעור לפרשה.')),preview?.id===study?.id&&preview.text?.[S.lang]?el('blockquote',{},preview.text[S.lang]+'…'):null,a(study?.url||'https://moriahise.github.io/Zohar/',study?T('Read this week’s Zohar →','לקריאת זוהר השבוע ←'):T('Open the Zohar library →','לספריית הזוהר ←')));
 const q=normalize(S.zoharQuery);const readings=allParashot(S.eco?.zohar).filter(p=>!q||normalize(p.en+p.he).includes(q));
 put('zohar-directory',...readings.map(p=>el('div',{class:'zohar-row'+(week&&normalize(p.he)===normalize(week.reading.he)?' current-reading':'')},el('span',{class:'zohar-number'},String(p.index+1).padStart(2,'0')),p.edition?a(p.edition.url,S.lang==='he'?p.he:p.en,''):el('span',{},S.lang==='he'?p.he:p.en),el('small',{},p.edition?T('Study available','לימוד זמין'):T('In the annual programme','בתוכנית השנתית')))));
 $('zohar-search').placeholder=T('Find a parashah…','חיפוש פרשה…');
}
function renderDictionary(){
 const word=$('dictionary-query')?.value||'תורה';
 put('dictionary-label',T('Look up a Hebrew or Aramaic word','חיפוש מילה בעברית או בארמית'));
 put('dictionary-tools',...['תורה','שבת','אור','שלום'].map(w=>button(w,()=>{$('dictionary-query').value=w;openDictionary(w);})),a('https://moriahise.github.io/Jastrow/',T('Open full dictionary ↗','למילון המלא ↖')));
 $('dictionary-submit').textContent=T('Search dictionary','חיפוש במילון');$('dictionary-close').textContent=T('Close dictionary window','סגירת חלון המילון');
}
function openDictionary(word){const q=String(word||'').trim();if(!q)return;const url='https://moriahise.github.io/Jastrow/#'+new URLSearchParams({view:'dictionary',q});const frame=el('iframe',{src:url,title:T('Jastrow dictionary','מילון יסטרוב'),class:'dictionary-iframe',loading:'lazy',referrerpolicy:'no-referrer'});put('dictionary-frame',frame,a(url,T('Open this search in a new tab ↗','פתיחת החיפוש בלשונית חדשה ↖')));$('dictionary-embed').hidden=false;}
function applyLabels(){
 const labels={hubEyebrow:['YOUR DAILY BEIT MIDRASH','בית המדרש היומי שלכם'],hubTitle:['Learn. Listen. Return to the source.','ללמוד. להאזין. לחזור למקור.'],hubNote:['The current readings and today’s daf, connected to your study libraries.','פרשות השבוע והדף היומי, מחוברים לספריות הלימוד שלכם.'],calendarEyebrow:['THE JEWISH CALENDAR','הלוח היהודי'],calendarTitle:['Every day, in its own time.','כל יום והזמן שלו.'],calendarNote:['Hebrew & civil dates · holidays · readings · local daily times','תאריכים עבריים ולועזיים · מועדים · קריאות · זמני היום'],calendarDetail:['Selected date & daily times','התאריך הנבחר וזמני היום'],calendarCredit:['Calendar and times: Hebcal. The Hebrew date changes at local sunset. City settings also select Israel or Diaspora observance.','לוח וזמנים: Hebcal. התאריך העברי מתחלף בשקיעה המקומית. בחירת העיר קובעת גם את מנהג ישראל או תפוצות.'],musicEyebrow:['THE NIGGUN ROOM','חדר הניגון'],musicTitle:['A melody. A playlist. A journey.','מנגינה. פלייליסט. מסע.'],musicNote:['Nine collections, changing selections and series from your song library.','תשעה אוספים, בחירות מתחלפות וסדרות מתוך ספריית השירים שלכם.'],qaEyebrow:['FROM THE SANHEDRIN LIBRARY','מתוך ספריית סנהדרין'],qaTitle:['A question opens a conversation.','שאלה פותחת שיחה.'],qaNote:['Real questions with existing answers. Selections change daily; excerpts lead to the full original context.','שאלות אמיתיות עם תשובות קיימות. הבחירה מתחלפת מדי יום; התקציר מפנה להקשר המלא במקור.'],zoharEyebrow:['ZOHAR · THROUGH THE WHOLE TORAH','זוהר · לאורך התורה כולה'],zoharTitle:['Every parashah has its place.','לכל פרשה יש מקום.'],zoharNote:['All 54 readings are visible. Published lessons open directly; future lessons are clearly identified.','כל 54 הפרשות מופיעות. שיעורים שפורסמו נפתחים ישירות; פרשות שטרם פורסמו מסומנות בבירור.'],dictionaryEyebrow:['THE WORD & ITS SOURCES','המילה ומקורותיה'],dictionaryTitle:['Keep a dictionary beside the text.','מילון לצד הטקסט.'],dictionaryNote:['Jastrow · Klein · BDB · Strong’s. Search here and continue in the complete dictionary.','יסטרוב · קליין · BDB · סטרונג. חפשו כאן והמשיכו במילון המלא.'],dafEyebrow:['THE DAILY DAF','הדף היומי'],dafTitle:['One daf. Every day.','דף אחד. בכל יום.'],dafNote:['Changes with the civil date in Israel. Open the actual daily study or choose another date.','מתעדכן עם התאריך האזרחי בישראל. פתחו את הלימוד היומי או בחרו תאריך אחר.']};
 for(const n of document.querySelectorAll('[data-extra-label]')){const v=labels[n.dataset.extraLabel];if(v)n.textContent=v[S.lang==='he'?1:0];}
 const nav=[['jewish-calendar','Calendar','לוח'],['niggunim','Niggunim & playlists','ניגונים ופלייליסטים'],['questions','Questions & answers','שאלות ותשובות'],['zohar','Zohar','זוהר'],['dictionary','Jastrow dictionary','מילון יסטרוב'],['daily-daf','Daily daf','הדף היומי']];
 put('ecosystem-nav',...nav.map(([id,en,he])=>el('a',{href:'#'+id},T(en,he))));
}
function render(context){S.data=context.data;S.eco=context.ecosystem;S.lang=context.lang;S.city=context.city;if(!S.data||!S.eco)return;applyLabels();renderDaf();weeklyLinks();renderMonth();renderMusic();renderQA();renderZohar();renderDictionary();S.lastDay=civilDate();}
window.MoriahExtras={render};
if($('dictionary-form'))$('dictionary-form').addEventListener('submit',e=>{e.preventDefault();openDictionary($('dictionary-query').value);});
$('dictionary-close')?.addEventListener('click',()=>{put('dictionary-frame');$('dictionary-embed').hidden=true;});
$('zohar-search')?.addEventListener('input',e=>{S.zoharQuery=e.target.value;renderZohar();});
setInterval(()=>{if(!S.data||document.hidden)return;const hd=calendarClock();if(S.lastHebAbs!==hd.abs()){if(!S.monthManual)S.cursor=null;S.selected=isoHDate(hd);renderMonth();}if(S.lastDay!==civilDate()){S.lastDay=civilDate();renderDaf();weeklyLinks();renderMonth();renderQA();renderZohar();}},30000);
setInterval(()=>{if(!S.data||S.playing||document.hidden||$('niggunim')?.contains(document.activeElement))return;if(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)return;S.collection=null;S.musicOffset++;renderMusic();},90000);
