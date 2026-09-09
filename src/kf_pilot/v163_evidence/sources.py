import csv
import hashlib
from pathlib import Path
import re
from html.parser import HTMLParser

from kf_pilot.v162_remediation.core import require


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip and data.strip():self.parts.append(data.strip())


def source_catalog(root):
    """Extract only manifest-pinned original assets, never network or derivatives."""
    import pymupdf
    catalog = {}
    base = (root/'farming_input/files').resolve()
    for row in csv.DictReader((root/'farming_input/resource_manifest.csv').open(encoding='utf-8-sig')):
        if row['legal_status'] == 'NORMALIZED_DERIVATIVE':
            continue
        path = (base/row['file_path']).resolve()
        require(path.is_relative_to(base), 'source path escapes input directory')
        if not path.exists():
            continue
        raw = path.read_bytes()
        h = hashlib.sha256(raw).hexdigest()
        require(h == row['content_sha256'], 'SOURCE_HASH_MISMATCH: '+row['resource_id'])
        if path.suffix == '.pdf':
            with pymupdf.open(path) as pdf:
                bounds = row['page_scope'].split('-')
                numbers = range(len(pdf)) if row['page_scope'] == 'ALL' else range(int(bounds[0])-1,int(bounds[-1]))
                texts = {f'pdf:page:{n+1}': pdf[n].get_text(sort=True) for n in numbers}
            extractor = 'pymupdf:'+pymupdf.VersionBind+':sort=True'
        elif path.suffix == '.html':
            parser=VisibleText();parser.feed(raw.decode('utf-8'))
            texts = {'html:visible-text': ' '.join(parser.parts)}
            extractor = 'stdlib.HTMLParser:UTF8:skip-script-style:join-space:v1'
        else:
            continue
        catalog[row['original_url']] = dict(source_ref=row['original_url'],path=str(path.relative_to(root)),
            content_sha256=h, authority_tier=row['authority_tier'], applicability=row['applicability_scope'],
            extractor=extractor,texts=texts)
    return catalog


def find_spans(source, quote):
    """Whitespace-tolerant search returns exact extracted text, never a rewritten quote."""
    pattern = r'\s+'.join(re.escape(w) for w in quote.split())
    if not pattern:return []
    out=[]
    for locator,text in sorted(source['texts'].items()):
        for match in re.finditer(pattern,text):
            out.append(dict(source_ref=source['source_ref'],content_sha256=source['content_sha256'],
                locator=f'{locator}:chars:{match.start()}:{match.end()}',exact_quote=match.group(),
                context_before=text[max(0,match.start()-150):match.start()],context_after=text[match.end():match.end()+150]))
    return out


def verify_span(span,catalog):
    require(span['source_ref'] in catalog, 'SOURCE_UNAVAILABLE')
    source=catalog[span['source_ref']]
    require(span['content_sha256']==source['content_sha256'], 'source hash mismatch')
    parts=span['locator'].rsplit(':chars:',1)
    require(len(parts)==2 and parts[0] in source['texts'], 'locator mismatch')
    start,end=map(int,parts[1].split(':'))
    text=source['texts'][parts[0]]
    require(0<=start<end<=len(text), 'invalid source offsets')
    require(text[start:end]==span['exact_quote'], 'quote/locator mismatch')
    return source
