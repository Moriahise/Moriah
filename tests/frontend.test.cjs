const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const root=path.join(__dirname,'..');
async function setup(){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'web/index.html'),'utf8'),{url:'https://moriah.test/',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window;
 w.fetch=async url=>({ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(root,url),'utf8'))});
 w.HTMLElement.prototype.scrollIntoView=()=>{};
 w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
 w.HTMLDialogElement.prototype.close=function(){this.open=false;};
 w.eval(fs.readFileSync(path.join(root,'assets/app.js'),'utf8'));
 await new Promise(r=>setTimeout(r,70));
 return {dom,w,d:w.document};
}
test('front page renders live data, 24 sections and working archive links',async()=>{
 const {dom,d}=await setup();assert.equal(d.querySelectorAll('.news-card').length,18);assert.equal(d.querySelectorAll('#section-directory button').length,24);assert.ok(d.querySelectorAll('#latest-downloads a').length===2);assert.equal(d.querySelector('#error').hidden,true);dom.window.close();
});
test('switching Hebrew changes document direction, labels and content',async()=>{
 const {dom,d}=await setup();d.querySelector('[data-lang="he"]').click();assert.equal(d.documentElement.dir,'rtl');assert.equal(d.documentElement.lang,'he');assert.equal(d.querySelector('#lead-title').textContent,'אבן אחת — עולם שלם');assert.match(d.querySelector('#desk h2').textContent,/ישראל/);dom.window.close();
});
test('source filter limits results to the chosen publisher',async()=>{
 const {dom,w,d}=await setup();const s=d.querySelector('#source-filter');s.value='jpost';s.dispatchEvent(new w.Event('change'));const cards=[...d.querySelectorAll('.news-card')];assert.ok(cards.length>0);assert.ok(cards.every(x=>x.textContent.includes('The Jerusalem Post')));dom.window.close();
});
test('text search and clear handle empty results without changing data',async()=>{
 const {dom,w,d}=await setup();const s=d.querySelector('#search-input');s.value='zzzz-no-such-story-qqqq';s.dispatchEvent(new w.Event('input'));await new Promise(r=>setTimeout(r,160));assert.equal(d.querySelectorAll('.news-card').length,0);assert.ok(d.querySelector('.empty-state'));d.querySelector('#search-clear').click();assert.equal(d.querySelectorAll('.news-card').length,18);dom.window.close();
});
test('reading a feature opens a bilingual accessible dialog',async()=>{
 const {dom,d}=await setup();d.querySelector('#lead-read').click();assert.ok(d.querySelector('#article-dialog').open);assert.match(d.querySelector('#article-title').textContent,/stone/);d.querySelector('[data-lang="he"]').click();assert.match(d.querySelector('#article-title').textContent,/אבן/);d.querySelector('#close-dialog').click();assert.equal(d.querySelector('#article-dialog').open,false);dom.window.close();
});
test('load more expands only the news list',async()=>{
 const {dom,d}=await setup();const before=d.querySelectorAll('.news-card').length;d.querySelector('#load-more').click();assert.ok(d.querySelectorAll('.news-card').length>before);dom.window.close();
});

test('front-page focus gives original-language reports priority',async()=>{
 const {dom,d}=await setup();const first=[...d.querySelectorAll('#front-news .compact-item')];assert.ok(first.length>0);assert.ok(first.every(n=>!n.querySelector('.machine-label')));dom.window.close();
});
