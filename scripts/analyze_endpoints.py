"""Recalculate the six retained acquisitions from raw exports and the frozen map."""
from config import ROOT,OUT
from analyze_timeseries import parse_raw
from inputs import load_inputs
from statistics import mean,stdev
from hashlib import sha256
import csv,json,math

def close(actual,expected,tolerance=1e-10):
    assert math.isclose(float(actual),float(expected),rel_tol=tolerance,abs_tol=tolerance),(actual,expected)
def save(name,rows):
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

sources,details=load_inputs()
well_rows=[];group_rows=[];acquisitions=[]
for src in sources:
    idx=src['audit_index'];detail=details[idx];path=ROOT/src['path']
    assert sha256(path.read_bytes()).hexdigest()==src['sha256'],f"Changed source: {path}"
    sheet,metadata,channels,lag=parse_raw(path)
    target_h=detail['endpoint_h']
    nearest={c:min(channels[c]['reads'],key=lambda r:abs(r['seconds']-target_h*3600)) for c in ['OD','FL']}
    expected={r['well']:r for r in detail['reference_wells']}
    groups={};used=set()
    for entry in detail['groups']:
        name=entry['name'];values={}
        for condition in ['N','P']:
            wells=entry['wells'][condition]
            assert len(wells)==3 and not used.intersection(wells)
            used.update(wells);measurements=[]
            for w in wells:
                od=nearest['OD']['values'][w];fl=nearest['FL']['values'][w]
                assert od>0 and fl>=0
                y=fl/od;record=expected[w]
                assert record['group']==name and record['condition']==condition
                close(od,record['od600']);close(fl,record['fluorescence'])
                assert abs(y-record['normalized_rounded'])<=.00051
                measurements.append((od,fl,y))
                well_rows.append(dict(audit_index=idx,source=src['path'],sheet=sheet,group=name,condition=condition,well=w,
                    endpoint_h=target_h,od_time_h=nearest['OD']['seconds']/3600,fl_time_h=nearest['FL']['seconds']/3600,
                    od_excel_row=nearest['OD']['excel_row'],fl_excel_row=nearest['FL']['excel_row'],od600=od,fluorescence_au=fl,fluorescence_per_od=y))
            values[condition]=measurements
            assert abs(mean(v[2] for v in measurements)-entry['expected_means'][condition])<=.00051
        result=dict(audit_index=idx,acquisition=src['acquisition'],group=name,endpoint_h=target_h)
        for condition in ['N','P']:
            for j,metric in enumerate(['OD','FL','NORM']):
                vector=[v[j] for v in values[condition]]
                result[f'{condition}_{metric}_mean']=mean(vector)
                result[f'{condition}_{metric}_sd']=stdev(vector)
        result['PN_norm']=result['P_NORM_mean']/result['N_NORM_mean']
        result['NP_norm']=1/result['PN_norm'];groups[name]=result
    for name,result in groups.items():
        # These references reproduce the verified acquisition-specific controls.
        nt=None
        if idx==9:nt=next(k for k in groups if k.startswith(name[:3]) and '(NT)' in k)
        result['nt_group']=nt or ''
        result['PN_nt_adjusted']=result['PN_norm']/groups[nt]['PN_norm'] if nt else ''
        result['repression_nt_percent']=100*(1-result['PN_nt_adjusted']) if nt else ''
        group_rows.append(result)
    acquisitions.append(dict(audit_index=idx,source=src['path'],sheet=sheet,endpoint_h=target_h,
        od_channel=channels['OD']['name'],fl_channel=channels['FL']['name'],
        cycles=len(channels['OD']['reads']),last_od_h=channels['OD']['reads'][-1]['seconds']/3600,
        last_fl_h=channels['FL']['reads'][-1]['seconds']/3600,metadata_json=json.dumps(metadata,ensure_ascii=False)))
save('endpoint_wells.csv',well_rows);save('endpoint_groups.csv',group_rows);save('acquisition_metadata.csv',acquisitions)
print(f'Endpoint checks: {len(sources)} acquisitions, {len(group_rows)} groups, {len(well_rows)} wells')
