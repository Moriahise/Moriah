#!/usr/bin/env python3
"""Meaningful publication gate: PDF page count/text, local links and required data."""
import json,sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
from pypdf import PdfReader
from pipeline import ROOT,load,validate

class Links(HTMLParser):
 def __init__(self):super().__init__();self.refs=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  for k in ('href','src'):
   if a.get(k):self.refs.append(a[k])

def verify(root):
 validate(load(root/'data/latest.json'))
 failures=[]
 for f in root.rglob('*.html'):
  p=Links();p.feed(f.read_text())
  for ref in p.refs:
   s=urlsplit(ref)
   if s.scheme or ref.startswith(('#','/')):continue
   target=(f.parent/unquote(s.path)).resolve()
   if not target.exists():failures.append(f'{f.relative_to(root)} → {ref}')
 pdfs=list(root.rglob('*.pdf'))
 for p in pdfs:
  r=PdfReader(p)
  if len(r.pages)!=16:failures.append(f'{p.name}: {len(r.pages)} pages, expected 16')
  text=''.join(page.extract_text() or '' for page in r.pages)
  if len(text)<6000:failures.append(f'{p.name}: suspiciously little extractable text')
  if p.stem.endswith('-he') and sum('\u0590'<=c<='\u05ff' for c in text)<1500:failures.append(f'{p.name}: Hebrew text missing')
 if not pdfs:failures.append('No PDFs generated')
 if failures:
  print('\n'.join(failures));raise SystemExit(1)
 print(f'Publication gate passed: {len(pdfs)} PDFs (16 pages each), all generated local links resolve.')

if __name__=='__main__':verify(ROOT/'_site')
