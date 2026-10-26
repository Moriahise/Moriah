const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const root=path.join(__dirname,'..');
async function setup(t,{withoutTracks,news}={}){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'web/index.html'),'utf8'),{url:'https://moriah.test/',runScripts:'outside-only',pretendToBeVisual:true});
 t.after(()=>dom.window.close());
 const w=dom.window;
 let loadedData;
 const NativeDate=w.Date;w.Date=class extends NativeDate{constructor(...args){super(...(args.length?args:["2026-10-24T12:00:00Z"]));}static now(){return new NativeDate("2026-10-24T12:00:00Z").getTime();}};
 w.fetch=async url=>({ok:true,json:async()=>{const value=JSON.parse(fs.readFileSync(path.join(root,url),'utf8'));if(url==='data/latest.json'){if(news!==undefined)value.news=news;loadedData=value;}if(withoutTracks&&url==='data/ecosystem.json'){const collection=value.music.find(c=>c.id===withoutTracks);collection.tracks=[];collection.playlists=[];collection.series=[];}return value;}});
 w.HTMLElement.prototype.scrollIntoView=()=>{};
 w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
 w.HTMLDialogElement.prototype.close=function(){this.open=false;};
 w.eval(fs.readFileSync(path.join(root,'assets/integrations.js'),'utf8'));
 w.eval(fs.readFileSync(path.join(root,'assets/app.js'),'utf8'));
 await new Promise(r=>setTimeout(r,70));
 return {dom,w,d:w.document,data:loadedData};
}
test('front page renders live data, 24 sections and working archive links',async t=>{
 const {dom,d}=await setup(t);assert.equal(d.querySelectorAll('.news-card').length,18);assert.equal(d.querySelectorAll('#section-directory button').length,24);assert.ok(d.querySelectorAll('#latest-downloads a').length===2);assert.equal(d.querySelector('#error').hidden,true);
});
test('switching Hebrew changes document direction, labels and content',async t=>{
 const {dom,d}=await setup(t);d.querySelector('[data-lang="he"]').click();assert.equal(d.documentElement.dir,'rtl');assert.equal(d.documentElement.lang,'he');assert.equal(d.querySelector('#lead-title').textContent,'אבן אחת — עולם שלם');assert.match(d.querySelector('#desk h2').textContent,/ישראל/);
});
test('source filter limits results to the chosen publisher',async t=>{
 const {dom,w,d}=await setup(t);const s=d.querySelector('#source-filter');s.value='jpost';s.dispatchEvent(new w.Event('change'));const cards=[...d.querySelectorAll('.news-card')];assert.ok(cards.length>0);assert.ok(cards.every(x=>x.textContent.includes('The Jerusalem Post')));
});
test('text search and clear handle empty results without changing data',async t=>{
 const {dom,w,d}=await setup(t);const s=d.querySelector('#search-input');s.value='zzzz-no-such-story-qqqq';s.dispatchEvent(new w.Event('input'));await new Promise(r=>setTimeout(r,160));assert.equal(d.querySelectorAll('.news-card').length,0);assert.ok(d.querySelector('.empty-state'));d.querySelector('#search-clear').click();assert.equal(d.querySelectorAll('.news-card').length,18);
});
test('reading a feature opens a bilingual accessible dialog',async t=>{
 const {dom,d}=await setup(t);d.querySelector('#lead-read').click();assert.ok(d.querySelector('#article-dialog').open);assert.match(d.querySelector('#article-title').textContent,/stone/);d.querySelector('[data-lang="he"]').click();assert.match(d.querySelector('#article-title').textContent,/אבן/);d.querySelector('#close-dialog').click();assert.equal(d.querySelector('#article-dialog').open,false);
});
test('load more expands only the news list',async t=>{
 const {dom,d}=await setup(t);const before=d.querySelectorAll('.news-card').length;d.querySelector('#load-more').click();assert.ok(d.querySelectorAll('.news-card').length>before);
});

test('front-page focus prioritizes native source families and labels translated fallbacks',async t=>{
 const {d,data}=await setup(t),cards=[...d.querySelectorAll('#front-news .compact-item')];
 const selected=cards.map(n=>data.news.find(x=>x.url===n.querySelector('h3 a').href));
 const nativeFamilies=new Set(data.news.filter(x=>x.source_language==='en').map(x=>x.family));
 assert.equal(selected.length,Math.min(4,new Set(data.news.map(x=>x.family)).size));
 assert.equal(new Set(selected.map(x=>x.family)).size,selected.length);
 const nativeCount=Math.min(4,nativeFamilies.size);
 assert.ok(selected.slice(0,nativeCount).every(x=>x.source_language==='en'));
 assert.ok(selected.slice(nativeCount).every(x=>x.source_language!=='en'));
 for(let i=0;i<cards.length;i++)assert.equal(!!cards[i].querySelector('.machine-label'),selected[i].translation?.en==='machine');
});

function headline(id,language,family){
 return {id,url:'https://example.test/'+id,source_id:language==='en'?'jpost':'maariv',family,source_language:language,title:id,titles:{en:id,he:id},translation:{en:language==='en'?'original':'machine',he:language==='he'?'original':'machine'},published_at:'2026-10-24T10:00:00Z',section:'israel'};
}
function focusIds(d){return [...d.querySelectorAll('#front-news h3 a')].map(a=>new URL(a.href).pathname.slice(1));}
test('focus fills missing native families with clearly labelled translated reports',async t=>{
 const news=[headline('translated-a','he','foreign-a'),headline('native-a','en','native-a'),headline('shared-foreign','he','native-a'),headline('native-b','en','native-b'),headline('duplicate-native','en','native-a'),headline('translated-b','he','foreign-b')];
 const {d}=await setup(t,{news});
 assert.deepEqual(focusIds(d),['native-a','native-b','translated-a','translated-b']);
 assert.equal(d.querySelectorAll('#front-news .machine-label').length,2);
});
test('focus keeps translated reports out when four native families are available',async t=>{
 const news=[headline('translated','he','foreign'),...['a','b','c','d'].map(id=>headline(id,'en',id))];
 const {d}=await setup(t,{news});assert.deepEqual(focusIds(d),['a','b','c','d']);assert.equal(d.querySelectorAll('#front-news .machine-label').length,0);
});
test('focus handles no native reports and fewer than four families in both languages',async t=>{
 const news=[headline('a','he','a'),headline('a-duplicate','he','a'),headline('b','he','b'),headline('c','he','c')];
 const {d}=await setup(t,{news});assert.deepEqual(focusIds(d),['a','b','c']);assert.equal(d.querySelectorAll('#front-news .machine-label').length,3);
 d.querySelector('[data-lang="he"]').click();assert.deepEqual(focusIds(d),['a','b','c']);assert.equal(d.querySelectorAll('#front-news .machine-label').length,0);
});


test('all seven integrations render and weekly source links open exact studies',async t=>{
 const {dom,d}=await setup(t);
 for(const id of ['jewish-calendar','niggunim','questions','zohar','dictionary','daily-daf'])assert.ok(d.getElementById(id));
 assert.equal(d.querySelectorAll('#daily-cards .daily-card').length,3);
 assert.match(d.querySelector('#parashah-name a').href,/Shiurim\/shiur\//);assert.match(d.querySelector('#haftarah-name a').href,/Shiurim\/haftarot\/haftarah-/);
 assert.equal(d.querySelectorAll('.zohar-row').length,54);assert.equal(d.querySelectorAll('.qa-card').length,3);assert.equal(d.querySelectorAll('.collection-chip').length,9);
 assert.equal(d.querySelector('#error').hidden,true);
});
test('calendar navigation and selected-city daily times work in both languages',async t=>{
 const {dom,w,d}=await setup(t);const first=d.querySelector('#calendar-month-title').textContent;d.querySelector('#calendar-actions button:last-child').click();assert.notEqual(d.querySelector('#calendar-month-title').textContent,first);
 d.querySelector('#calendar-grid button').click();assert.equal(d.querySelectorAll('.zman-row').length>=8,true);
 const city=d.querySelector('#city-select');city.value='vienna';city.dispatchEvent(new w.Event('change'));assert.match(d.querySelector('#calendar-local-date').textContent,/Europe\/Vienna/);
 d.querySelector('[data-lang="he"]').click();assert.match(d.querySelector('#calendar-month-title').textContent,/[א-ת]/);assert.match(d.querySelector('#calendar-today').textContent,/[א-ת]/);
});
test('Niggunim rotate and create a real playlist player only after user choice',async t=>{
 const {dom,d}=await setup(t);assert.equal(d.querySelectorAll('#music-player iframe,#music-player audio').length,0);
 const before=d.querySelector('#music-feature h3').textContent;d.querySelector('#music-rotation button:last-child').click();assert.notEqual(d.querySelector('#music-feature h3').textContent,before);
 d.querySelector('#music-feature button').click();assert.ok(d.querySelector('#music-player iframe,#music-player audio'));assert.ok(d.querySelectorAll('#music-player button').length>=3);
 [...d.querySelectorAll('#music-player button')].at(-1).click();assert.equal(d.querySelectorAll('#music-player iframe,#music-player audio').length,0);
});
test('dictionary submits supported hash search and Q&A cards rotate',async t=>{
 const {dom,w,d}=await setup(t);d.querySelector('#dictionary-query').value='תורה';d.querySelector('#dictionary-form').dispatchEvent(new w.Event('submit',{cancelable:true}));
 const u=new URL(d.querySelector('#dictionary-frame iframe').src),params=new URLSearchParams(u.hash.slice(1));assert.equal(u.pathname,'/Jastrow/');assert.equal(params.get('view'),'dictionary');assert.equal(params.get('q'),'תורה');
 d.querySelector('#dictionary-close').click();assert.equal(d.querySelector('#dictionary-embed').hidden,true);
 const before=d.querySelector('#qa-cards h3').textContent;d.querySelector('#qa-actions button').click();assert.notEqual(d.querySelector('#qa-cards h3').textContent,before);
});
test('selected Daf date has its own reader while today card retains today',async t=>{
 const {dom,w,d}=await setup(t);const today=d.querySelector('.daf-feature h3 a').href;const input=d.querySelector('#daf-current input');input.value='2026-10-25';input.dispatchEvent(new w.Event('change'));assert.match(d.querySelector('#daf-current h3 a').href,/bekhorot-37/);assert.equal(d.querySelector('.daf-feature h3 a').href,today);
});

test('Beit haMikdash haShlishi opens its collection when no parsed tracks exist',async t=>{
 const {dom,d}=await setup(t,{withoutTracks:'Beit-haMikdash-haShlishi'});const link=[...d.querySelectorAll('#music-collections a')].find(n=>n.textContent.includes('Beit haMikdash haShlishi'));
 assert.ok(link);assert.equal(link.href,'https://moriahise.github.io/Beit-haMikdash-haShlishi/');assert.equal(link.target,'_blank');
 const other=d.querySelector('#music-collections button'),selectedTitle=other.textContent;other.click();assert.equal(d.querySelector('#music-feature h3').textContent,selectedTitle);
 assert.ok([...d.querySelectorAll('#music-collections button')].some(n=>n.getAttribute('aria-pressed')==='true'));
 
});
test('Minhal opens inline on request, preserves the scene across language changes and unloads on close',async t=>{
 const {dom,d}=await setup(t);const open=d.querySelector('#minhal-open');
 assert.equal(d.querySelectorAll('#minhal-frame iframe').length,0);assert.equal(d.querySelector('#minhal-embed').hidden,true);
 const overview=d.querySelector('#minhal-mikdash a[data-extra-label="minhalOverview"]');assert.equal(overview.href,'https://moriahise.github.io/Minhal-haMikdash/app/');assert.equal(overview.target,'_blank');
 open.click();const frame=d.querySelector('#minhal-frame iframe');assert.equal(frame.src,'https://moriahise.github.io/Minhal-haMikdash/app/Minhal_HaMikdash_Lebendiges_13.1.html');assert.equal(d.querySelector('#minhal-embed').hidden,false);assert.equal(open.getAttribute('aria-expanded'),'true');
 open.click();assert.equal(d.querySelectorAll('#minhal-frame iframe').length,1);
 d.querySelector('[data-lang="he"]').click();assert.equal(d.querySelector('#minhal-frame iframe'),frame);assert.match(frame.title,/מנהל המקדש/);assert.equal(open.textContent,'פתיחה בתוך מוריה');
 d.querySelector('#minhal-close').click();assert.equal(d.querySelectorAll('#minhal-frame iframe').length,0);assert.equal(d.querySelector('#minhal-embed').hidden,true);assert.equal(open.getAttribute('aria-expanded'),'false');assert.equal(d.activeElement,open);
});

