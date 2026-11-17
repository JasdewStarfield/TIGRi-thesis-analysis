"""Reconstruct time courses from raw exports using the verified well map.

The original files and thesis are read only. Endpoint checks reproduce the
previous audit before any new descriptive comparisons or plots are made.
"""
from datetime import time, timedelta
from hashlib import sha256
import csv
import json
import re
from collections import OrderedDict
from openpyxl import load_workbook
import numpy as np

from config import ROOT, OUT, AUDIT
from inputs import load_inputs

# Selection is based on the previous endpoint comparisons, before inspecting
# the time courses. All mapped groups on these plates are retained in tables.
SPECS = [
    (0, 'may12', '12 May: baseline repression', 10, 'repression',
     [('2A','2A'), ('2B','2B'), ('4A','4A')]),
    (2, 'may29', '29 May: native and BoxB configurations', 10, 'repression',
     [('native 2A','Native 2A'), ('BoxB 2A','BoxB 2A'),
      ('native 3A','Native 3A'), ('BoxB 3A','BoxB 3A')]),
    (3, 'jun08', '8 June: TadA8e fusion batch 1', 15, 'repression',
     [('088','dTasR'), ('132','N-GS15'), ('136','N-Rigid10'), ('142','C-Rigid5')]),
    (4, 'jun11', '11 June: TadA8e fusion batch 2', 14, 'repression',
     [('088','dTasR'), ('137','N-Rigid20'), ('140','C-GS10')]),
    (9, 'jul21i', '21 July: matched-site repression', 10, 'repression',
     [('088 / 165 (T7)','dTasR T7'), ('164 / 161 (T7)','dSpyCas9 T7'),
      ('088 / 166 (T8)','dTasR T8'), ('164 / 162 (T8)','dSpyCas9 T8'),
      ('088 / 168 (NT)','dTasR NT'), ('164 / 169 (NT)','dSpyCas9 NT')]),

]

def seconds(value):
    """Excel exports store elapsed time as time objects or day fractions."""
    if isinstance(value, time):
        return value.hour*3600 + value.minute*60 + value.second + value.microsecond/1e6
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, (float, int)):
        return float(value)*86400
    if isinstance(value, str) and re.fullmatch(r'\d+:\d\d:\d\d', value):
        h,m,s = map(int,value.split(':'))
        return h*3600+m*60+s
    return None

def parse_raw(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    sheet = wb.worksheets[0]
    name = sheet.title
    rows = list(sheet.values)
    wb.close()
    meta = {str(r[0]): str(r[1]) for r in rows[:30] if r[0] is not None}
    channels = {}
    for i,r in enumerate(rows):
        if not isinstance(r[0],str) or not re.match(r'^Read [12]:',r[0]):
            continue
        header = rows[i+2]
        assert 'Time' in header
        ti = header.index('Time')
        wells = {x:j for j,x in enumerate(header)
                 if isinstance(x,str) and re.fullmatch(r'[A-H](?:[1-9]|1[0-2])',x)}
        assert len(wells)==96
        series = []
        # Stop at the next read block; empty scheduled readings are not data.
        for ri in range(i+3,len(rows)):
            rr = rows[ri]
            if isinstance(rr[0],str) and rr[0].startswith('Read '):
                break
            ts = seconds(rr[ti])
            values = {w:float(rr[j]) for w,j in wells.items()
                      if isinstance(rr[j],(int,float)) and not isinstance(rr[j],bool)}
            if values and ts is not None:
                assert len(values)==96, f'Partial raw read: {path}, row {ri+1}'
                series.append({'seconds':ts,'excel_row':ri+1,'values':values})
        channel = 'OD' if r[0].endswith(':600') else 'FL'
        assert channel not in channels
        assert series and np.all(np.diff([v['seconds'] for v in series])>0)
        channels[channel] = {'name':r[0], 'reads':series}
    assert set(channels)=={'OD','FL'}
    od,fl = channels['OD']['reads'],channels['FL']['reads']
    assert len(od)==len(fl)
    # Both channels belong to the same acquisition cycle; no interpolation.
    lag = np.array([f['seconds']-o['seconds'] for o,f in zip(od,fl)])
    # The old reader measured fluorescence first (55 s before OD); the newer
    # exports measured OD first (43 s before fluorescence). Retain this sign.
    expected_sign = 1 if list(channels)[0]=='OD' else -1
    assert np.all((lag*expected_sign>=0)&(abs(lag)<120)), f'Unexpected channel lag: {path}'
    return name,meta,channels,lag

def write_csv(name,rows):
    if not rows:
        return
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def ratio(group,oi,fi):
    """Ratio of condition means of per-well fluorescence/OD, as in thesis."""
    y = {c:group[c]['FL'][fi]/group[c]['OD'][oi] for c in ['N','P']}
    return float(y['P'].mean()/y['N'].mean())

def nt_name(pid,g,all_groups):
    if pid=='jul21i':
        return next(x for x in all_groups if x.startswith(g[:3]) and '(NT)' in x)
    return None

def calculate():
    sources,details=load_inputs()
    source_by_id={x['audit_index']:x for x in sources}
    endpoint_rows=[]; well_rows=[]; group_rows=[]; manifests=[]; plates={}; consistency=[]
    for index,pid,title,endpoint,mode,selection in SPECS:
        d=details[index]
        source=ROOT/source_by_id[index]['path']
        sheet,meta,ch,lag=parse_raw(source)
        od,fl=ch['OD']['reads'],ch['FL']['reads']
        ot=np.array([x['seconds']/3600 for x in od]);ft=np.array([x['seconds']/3600 for x in fl])
        selected=dict(selection)
        groups=OrderedDict()
        seen=set()
        for entry in d['groups']:
            key=entry['name']
            wells=entry['wells']
            assert all(len(ws)==3 for ws in wells.values())
            g={}
            for c,ws in wells.items():
                assert not seen.intersection(ws)
                seen.update(ws)
                o=np.array([[r['values'][w] for w in ws] for r in od])
                f=np.array([[r['values'][w] for w in ws] for r in fl])
                assert np.all(np.isfinite(o)) and np.all(o>0)
                assert np.all(np.isfinite(f)) and np.all(f>=0)
                g[c]={'wells':ws,'OD':o,'FL':f,'NORM':f/o}
                for ti in range(len(od)):
                    for wi,w in enumerate(ws):
                        well_rows.append(dict(plate=pid,source=str(source.relative_to(ROOT)),sheet=sheet,
                            group=key,selected=int(key in selected),condition=c,well=w,colony_order=wi+1,
                            cycle=ti+1,od_time_h=ot[ti],fl_time_h=ft[ti],od_excel_row=od[ti]['excel_row'],
                            fl_excel_row=fl[ti]['excel_row'],od600=o[ti,wi],fluorescence_au=f[ti,wi],
                            fluorescence_per_od=f[ti,wi]/o[ti,wi]))
            groups[key]=g
            oi=int(np.argmin(abs(ot-endpoint)));fi=int(np.argmin(abs(ft-endpoint)))
            for c in ['N','P']:
                actual=float(np.mean(g[c]['FL'][fi]/g[c]['OD'][oi]))
                assert abs(actual-entry['expected_means'][c])<0.00051
            consistency.append({'plate':pid,'group':key,'prior_endpoint_h':endpoint,
                                'matches_prior_audit':True})
        assert set(selected)<=set(groups)
        for key,g in groups.items():
            nt=nt_name(pid,key,groups)
            raw=g['P']['NORM'].mean(axis=1)/g['N']['NORM'].mean(axis=1)
            adjusted=raw/(groups[nt]['P']['NORM'].mean(axis=1)/groups[nt]['N']['NORM'].mean(axis=1)) if nt else None
            for ti in range(len(od)):
                entry={'plate':pid,'group':key,'selected':int(key in selected),'cycle':ti+1,
                       'od_time_h':ot[ti],'fl_time_h':ft[ti]}
                for c in ['N','P']:
                    for metric in ['OD','FL','NORM']:
                        vals=g[c][metric][ti]
                        entry[f'{c}_{metric}_mean']=float(vals.mean())
                        entry[f'{c}_{metric}_sd']=float(vals.std(ddof=1))
                entry.update(PN_norm=raw[ti],NP_norm=1/raw[ti],
                             PN_raw_fluorescence=float(g['P']['FL'][ti].mean()/g['N']['FL'][ti].mean()),
                             PN_od=float(g['P']['OD'][ti].mean()/g['N']['OD'][ti].mean()),
                             nt_group=nt or '',PN_nt_adjusted=float(adjusted[ti]) if nt else '',
                             repression_nt_percent=float(100*(1-adjusted[ti])) if nt else '')
                group_rows.append(entry)
            # A fixed time grid prevents choosing the most favourable endpoint.
            grid=sorted(set([2,4,6,8,10,12,14,16,18,20,24,endpoint]))
            grid=[(str(t)+' h',float(t)) for t in grid if t<=min(ot[-1],ft[-1])+1/12]
            grid.append(('Final',float(ft[-1])))
            for tag,t in grid:
                oi=int(np.argmin(abs(ot-t)));fi=int(np.argmin(abs(ft-t)))
                r=ratio(g,oi,fi)
                adj=r/ratio(groups[nt],oi,fi) if nt else None
                entry=dict(plate=pid,group=key,label=selected.get(key,key),selected=int(key in selected),
                    nominal_endpoint=tag,nominal_h=t,od_time_h=ot[oi],fl_time_h=ft[fi],
                    od_excel_row=od[oi]['excel_row'],fl_excel_row=fl[fi]['excel_row'],
                    prior_endpoint=int(tag==str(endpoint)+' h'),PN_norm=r,NP_norm=1/r,
                    PN_raw_fluorescence=float(g['P']['FL'][fi].mean()/g['N']['FL'][fi].mean()),
                    PN_od=float(g['P']['OD'][oi].mean()/g['N']['OD'][oi].mean()),
                    nt_group=nt or '',PN_nt_adjusted=adj if adj is not None else '',
                    repression_nt_percent=100*(1-adj) if adj is not None else '')
                for c in ['N','P']:
                    vals={'OD':g[c]['OD'][oi], 'FL':g[c]['FL'][fi], 'NORM':g[c]['FL'][fi]/g[c]['OD'][oi]}
                    for metric,v in vals.items():
                        entry[f'{c}_{metric}_mean']=float(v.mean())
                        entry[f'{c}_{metric}_sd']=float(v.std(ddof=1))
                endpoint_rows.append(entry)
        manifest=dict(plate=pid,title=title,source=str(source.relative_to(ROOT)),source_sha256=sha256(source.read_bytes()).hexdigest(),
            sheet=sheet,meta=meta,od_channel=ch['OD']['name'],fl_channel=ch['FL']['name'],
            n_cycles=len(od),first_od_h=ot[0],last_od_h=ot[-1],first_fl_h=ft[0],last_fl_h=ft[-1],
            channel_lag_s_min=float(lag.min()),channel_lag_s_max=float(lag.max()),
            reference_endpoint_h=endpoint,mode=mode,selected=selection,mapped_groups=len(groups),
            map_evidence='Frozen assay_map.json; N/P are cultures split from independent colony-derived overnight cultures.')
        manifests.append(manifest)
        plates[pid]={'manifest':manifest,'groups':groups,'ot':ot,'ft':ft}
    write_csv('well_timeseries.csv',well_rows)
    write_csv('group_timeseries.csv',group_rows)
    write_csv('endpoint_comparison.csv',endpoint_rows)
    write_csv('historical_endpoint_checks.csv',consistency)
    (OUT/'manifest.json').write_text(json.dumps({'audit_sha256':sha256(AUDIT.read_bytes()).hexdigest(),
        'plates':manifests,'historical_groups_checked':len(consistency),'well_time_observations':len(well_rows),
        'normalization':'per-well F/OD, then condition means; ratios of condition means',
        'blank_subtraction':False,'excluded_acquisition':'1 August old: unverified well map',
        'time_series_alignment':'OD and FL from the same recorded cycle; actual times retained',
        'endpoint_alignment':'nearest measured time in each channel; no extrapolation',
        'sensitivity_grid_h':[2,4,6,8,10,12,14,16,18,20,24],
        'statistics':'descriptive; three colony-derived cultures; no time-point pseudoreplication'},
        ensure_ascii=False,indent=2),encoding='utf-8')
    return plates,endpoint_rows,group_rows

if __name__ == "__main__":
    plates, endpoints, groups = calculate()
    print(f"Time-series analysis: {len(plates)} acquisitions; {len(groups)} group-time rows")
