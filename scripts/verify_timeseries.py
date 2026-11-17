"""Independently check raw OOXML cells, CSV arithmetic and source preservation."""
from zipfile import ZipFile
from collections import defaultdict
from hashlib import sha256
from statistics import mean, stdev
from lxml import etree as E
from openpyxl.utils import get_column_letter
import csv
import json
import math

from config import ROOT, OUT, AUDIT
from inputs import load_inputs
m=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def read_csv(name):
    with (OUT/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def close(a,b,tol=1e-10):
    assert math.isclose(float(a),float(b),rel_tol=tol,abs_tol=tol),(a,b)

raw={}
for p in m['plates']:
    file=ROOT/p['source']
    assert sha256(file.read_bytes()).hexdigest()==p['source_sha256']
    with ZipFile(file) as z:
        # Read numeric cell storage directly, independently of openpyxl values.
        # All selected exports use the first physical sheet for the raw data.
        xml=E.fromstring(z.read('xl/worksheets/sheet1.xml'))
        raw[p['plate']]={c.get('r'):float(c.find('s:v',ns).text)
                         for c in xml.findall('.//s:sheetData/s:row/s:c',ns)
                         if c.get('t') in [None,'n'] and c.find('s:v',ns) is not None}

well_rows=read_csv('well_timeseries.csv')
groups=defaultdict(list)
for r in well_rows:
    letter=r['well'][0];number=int(r['well'][1:])
    # A1..A12, B1..B12,... start at column D in all instrument export headers.
    col=get_column_letter(4+(ord(letter)-ord('A'))*12+number-1)
    cells=raw[r['plate']]
    od=cells[col+r['od_excel_row']];fl=cells[col+r['fl_excel_row']]
    close(r['od600'],od);close(r['fluorescence_au'],fl)
    close(r['fluorescence_per_od'],fl/od)
    # The XML time column is in Excel day units; CSV stores hours.
    close(r['od_time_h'],cells['B'+r['od_excel_row']]*24,tol=1e-8)
    close(r['fl_time_h'],cells['B'+r['fl_excel_row']]*24,tol=1e-8)
    groups[(r['plate'],r['group'],r['cycle'],r['condition'])].append((od,fl,fl/od))

time_rows=read_csv('group_timeseries.csv')
for r in time_rows:
    for c in ['N','P']:
        vv=groups[(r['plate'],r['group'],r['cycle'],c)]
        assert len(vv)==3
        for i,metric in enumerate(['OD','FL','NORM']):
            close(r[f'{c}_{metric}_mean'],mean(v[i] for v in vv))
            close(r[f'{c}_{metric}_sd'],stdev(v[i] for v in vv))
    close(r['PN_norm'],float(r['P_NORM_mean'])/float(r['N_NORM_mean']))
    close(r['PN_norm'],1/float(r['NP_norm']))

# Verify all endpoint summaries using the full-precision per-well rows and
# their separate OD/fluorescence source-row addresses (not rounded summaries).
mapped=defaultdict(dict)
for r in well_rows:
    mapped[(r['plate'],r['group'],r['condition'])][r['well']]=None
endpoint_rows=read_csv('endpoint_comparison.csv')
for r in endpoint_rows:
    computed={}
    for c in ['N','P']:
        vv=[]
        for well in mapped[(r['plate'],r['group'],c)]:
            col=get_column_letter(4+(ord(well[0])-ord('A'))*12+int(well[1:])-1)
            od=raw[r['plate']][col+r['od_excel_row']]
            fl=raw[r['plate']][col+r['fl_excel_row']]
            vv.append(fl/od)
        computed[c]=mean(vv)
        close(r[f'{c}_NORM_mean'],computed[c])
    close(r['PN_norm'],computed['P']/computed['N'])
    if r['nt_group']:
        reference=next(x for x in endpoint_rows if x['plate']==r['plate'] and x['group']==r['nt_group']
                       and x['nominal_endpoint']==r['nominal_endpoint'])
        close(r['PN_nt_adjusted'],float(r['PN_norm'])/float(reference['PN_norm']))
        close(r['repression_nt_percent'],100*(1-float(r['PN_nt_adjusted'])))


# Numeric verification is retained; historical report rendering and manuscript
# immutability checks belong to document production, not the analysis package.
assert sha256(AUDIT.read_bytes()).hexdigest()==m['audit_sha256']

# Independently verify all six endpoint acquisitions, including the August NT
# panel, which is not part of the five-acquisition time-series reconstruction.
sources,_=load_inputs()
endpoint_raw={}
for source in sources:
    file=ROOT/source['path']
    assert sha256(file.read_bytes()).hexdigest()==source['sha256']
    with ZipFile(file) as archive:
        xml=E.fromstring(archive.read('xl/worksheets/sheet1.xml'))
        endpoint_raw[str(source['audit_index'])]={c.get('r'):float(c.find('s:v',ns).text)
            for c in xml.findall('.//s:sheetData/s:row/s:c',ns)
            if c.get('t') in [None,'n'] and c.find('s:v',ns) is not None}
endpoint_wells=read_csv('endpoint_wells.csv')
endpoint_groups=defaultdict(list)
for r in endpoint_wells:
    cells=endpoint_raw[r['audit_index']]
    col=get_column_letter(4+(ord(r['well'][0])-ord('A'))*12+int(r['well'][1:])-1)
    od=cells[col+r['od_excel_row']];fl=cells[col+r['fl_excel_row']]
    close(r['od600'],od);close(r['fluorescence_au'],fl);close(r['fluorescence_per_od'],fl/od)
    close(r['od_time_h'],cells['B'+r['od_excel_row']]*24,tol=1e-8)
    close(r['fl_time_h'],cells['B'+r['fl_excel_row']]*24,tol=1e-8)
    endpoint_groups[(r['audit_index'],r['group'],r['condition'])].append((od,fl,fl/od))
endpoint_summaries=read_csv('endpoint_groups.csv')
for r in endpoint_summaries:
    for condition in ['N','P']:
        values=endpoint_groups[(r['audit_index'],r['group'],condition)]
        assert len(values)==3
        for j,metric in enumerate(['OD','FL','NORM']):
            close(r[f'{condition}_{metric}_mean'],mean(v[j] for v in values))
            close(r[f'{condition}_{metric}_sd'],stdev(v[j] for v in values))
    close(r['PN_norm'],float(r['P_NORM_mean'])/float(r['N_NORM_mean']))
    close(r['NP_norm'],1/float(r['PN_norm']))
    if r['nt_group']:
        nt=next(x for x in endpoint_summaries if x['audit_index']==r['audit_index'] and x['group']==r['nt_group'])
        close(r['PN_nt_adjusted'],float(r['PN_norm'])/float(nt['PN_norm']))
        close(r['repression_nt_percent'],100*(1-float(r['PN_nt_adjusted'])))
result={'raw_cells_checked':len(well_rows)*2,'well_time_rows':len(well_rows),
        'group_time_rows':len(time_rows),'endpoint_rows':len(endpoint_rows),
        'historical_groups_reproduced':m['historical_groups_checked'],
        'endpoint_acquisitions':len(sources),'endpoint_wells':len(endpoint_wells),
        'endpoint_raw_cells_checked':len(endpoint_wells)*2,'endpoint_groups':len(endpoint_summaries)}
(OUT/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
