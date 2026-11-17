"""Recreate the displayed cells of final supplementary Tables D1 and D2."""
from config import OUT
import pandas as pd
import json,csv

ep=pd.read_csv(OUT/'endpoint_comparison.csv').fillna('')
manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))

def save(name,headers,rows):
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(headers);writer.writerows(rows)

def row(pid,key,tag):
    data=ep[(ep.plate==pid)&(ep.group==key)&(ep.nominal_endpoint==tag)]
    assert len(data)==1
    return data.iloc[0]

def f(value,n=2):
    return '—' if value=='' else f'{float(value):.{n}f}'

d1=[]
for plate in manifest['plates']:
    pid=plate['plate'];date=plate['title'].split(':')[0]
    for key,label in plate['selected']:
        original=row(pid,key,str(plate['reference_endpoint_h'])+' h')
        last=row(pid,key,'Final')
        values=[]
        for time in [6,10,14]:
            found=ep[(ep.plate==pid)&(ep.group==key)&(ep.nominal_endpoint==f'{time} h')]
            values.append(f(found.iloc[0].NP_norm) if len(found) else '—')
        d1.append([date,label]+values+[f(original.NP_norm)+' ('+str(plate['reference_endpoint_h'])+')',
                  f(last.NP_norm)+' ('+f(last.fl_time_h)+')'])
save('Table-D1.csv',['Date','Configuration','6 h','10 h','14 h','Original (h)','Final (h)'],d1)

# Use each effector's own NT condition. NT rows are references, not targeting tests.
d2=[];numeric=[]
for effector,prefix in [('dTasR','088'),('N-GS15','132')]:
    for site,guide in [('T7','165'),('T8','166'),('NT','168')]:
        r=row('jul21i',f'{prefix} / {guide} ({site})','10 h')
        d2.append([effector,site,f(r.N_NORM_mean,1)+' ± '+f(r.N_NORM_sd,1),
                   f(r.P_NORM_mean,1)+' ± '+f(r.P_NORM_sd,1),f(r.NP_norm),
                   'Reference' if site=='NT' else f(r.repression_nt_percent,1)])
        numeric.append({'group':r['group'],'effector':effector,'site':site,'N_mean':r.N_NORM_mean,
                        'N_sd':r.N_NORM_sd,'P_mean':r.P_NORM_mean,'P_sd':r.P_NORM_sd,
                        'NP':r.NP_norm,'PN_nt_adjusted':r.PN_nt_adjusted,
                        'corrected_repression_percent':r.repression_nt_percent})
save('Table-D2.csv',['Effector','Guide','N GFP/OD600','P GFP/OD600','N/P','NT-adjusted repression (%)'],d2)
with (OUT/'ngs15_summary.csv').open('w',encoding='utf-8-sig',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=list(numeric[0]));writer.writeheader();writer.writerows(numeric)
with (OUT/'endpoint_wells.csv').open(encoding='utf-8-sig',newline='') as stream:
    wells=[r for r in csv.DictReader(stream) if r['audit_index']=='9' and r['group'] in {x['group'] for x in numeric}]
assert len(wells)==36
with (OUT/'ngs15_wells.csv').open('w',encoding='utf-8-sig',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=list(wells[0]));writer.writeheader();writer.writerows(wells)
print('Created Tables D1 and D2, with full-precision N-GS15 results')
