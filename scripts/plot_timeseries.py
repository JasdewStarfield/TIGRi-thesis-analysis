"""Draw manuscript-sized vector time-course figures from verified CSV data."""
import json
import numpy as np
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pypdfium2

from config import OUT as DATA, FONT_REGULAR, FONT_BOLD
QA=DATA
ROOT=DATA
OUT=DATA/'figures'
OUT.mkdir(exist_ok=True)
W=pd.read_csv(DATA/'well_timeseries.csv')
G=pd.read_csv(DATA/'group_timeseries.csv')
BLUE='#28648a';ORANGE='#bd5a24';DARK='#304c5b';PURPLE='#8552a1'
COLORS=[DARK,ORANGE,PURPLE,'#409386']
pdfmetrics.registerFont(TTFont('Chart',str(FONT_REGULAR)))
pdfmetrics.registerFont(TTFont('ChartBold',str(FONT_BOLD)))

def groups(pid,key):
    return G[(G.plate==pid)&(G.group==key)].sort_values('cycle')

def curve(pid,key,metric,label,color=DARK,dash=()):
    d=groups(pid,key)
    return (d.fl_time_h.to_numpy(),d[metric].to_numpy(),label,color,1.5,dash)

def component(pid,key,metric):
    d=W[(W.plate==pid)&(W.group==key)]
    col={'OD':'od600','FL':'fluorescence_au','Y':'fluorescence_per_od'}[metric]
    tc='od_time_h' if metric=='OD' else 'fl_time_h'
    lines=[]
    for c,color,faint in [('N',BLUE,'#9bb9ce'),('P',ORANGE,'#e0b59b')]:
        sub=d[d.condition==c]
        for well in sorted(sub.well.unique()):
            a=sub[sub.well==well].sort_values('cycle')
            lines.append((a[tc].to_numpy(),a[col].to_numpy(),None,faint,.55,()))
        a=sub.groupby('cycle')[[tc,col]].mean()
        lines.append((a[tc].to_numpy(),a[col].to_numpy(),c,color,1.65,()))
    return lines

def panel(title,ylabel,lines,endpoint=None,xmin=0,yzero=True,one=False,percent=False):
    return dict(title=title,ylabel=ylabel,lines=lines,endpoint=endpoint,xmin=xmin,yzero=yzero,one=one,percent=percent)


def notation_label(cv,x,y,value,font,size,center=False):
    """Keep OD upright and draw its wavelength as a smaller, lowered suffix."""
    value=str(value)
    if 'OD600' not in value:
        (cv.drawCentredString if center else cv.drawString)(x,y,value)
        return
    parts=[]
    for idx,piece in enumerate(value.split('OD600')):
        if idx: parts.extend([('OD',size,0),('600',size*.7,-size*.22)])
        if piece: parts.append((piece,size,0))
    width=sum(pdfmetrics.stringWidth(s,font,sz) for s,sz,rise in parts)
    text=cv.beginText(x-width/2 if center else x,y)
    for s,sz,rise in parts:
        text.setFont(font,sz);text.setRise(rise);text.textOut(s)
    cv.drawText(text)

FIGURES={}

def draw(label,title,panels):
    """Two columns keep chart text readable at the thesis text width."""
    rows=(len(panels)+1)//2
    width=430;height=16+rows*151
    path=OUT/f'Figure-{label}-time-series.pdf'
    cv=canvas.Canvas(str(path),pagesize=(width,height));cv.setTitle(title)
    def text(x,y,s,size=8,color=DARK,bold=False):
        cv.setFont('ChartBold' if bold else 'Chart',size);cv.setFillColor(HexColor(color))
        notation_label(cv,x,height-y,s,'ChartBold' if bold else 'Chart',size)
    def line(x,y,x2,y2,color='#dce4e8',lw=.5,dash=()):
        cv.setStrokeColor(HexColor(color));cv.setLineWidth(lw);cv.setDash(dash)
        cv.line(x,height-y,x2,height-y2)
    for idx,p in enumerate(panels):
        xx=(idx%2)*215;yy=(idx//2)*151+9
        text(xx+3,yy,chr(65+idx)+'  '+p['title'],8.8,bold=True)
        text(xx+32,yy+12,p['ylabel'],7.7)
        lines=[]
        for t,v,lab,color,lw,dash in p['lines']:
            keep=t>=p['xmin'];lines.append((t[keep],v[keep],lab,color,lw,dash))
        legends=[s for s in lines if s[2] is not None]
        nlegend=(len(legends)+1)//2
        for j,(_,_,lab,color,lw,dash) in enumerate(legends):
            lx=xx+32+(j%2)*91;ly=yy+23+(j//2)*10
            line(lx,ly-2,lx+10,ly-2,color,lw,dash);text(lx+13,ly,lab,7.2)
        x0=xx+32;x1=xx+207;y0=yy+26+nlegend*10;y1=yy+125
        xmin=p['xmin'];xmax=max(float(t[-1]) for t,*_ in lines)
        if p['endpoint'] is not None:xmax=max(xmax,p['endpoint'])
        vmax=max(float(v.max()) for _,v,*_ in lines)
        actual_min=min(float(v.min()) for _,v,*_ in lines)
        vmin=min(0,actual_min) if p['yzero'] else actual_min
        if p['one']:vmax=max(vmax,1);vmin=min(vmin,1)
        if p['percent']:vmin=0;vmax=100
        span=vmax-vmin;order=10**np.floor(np.log10(max(span/3,1e-9)))
        step=next(x for x in [1,2,2.5,5,10] if x>=span/3/order)*order
        ymax=np.ceil(vmax/step)*step;ymin=np.floor(vmin/step)*step
        if p['percent']:step=25;ymax=100;ymin=0
        xp=lambda v:x0+(v-xmin)/(xmax-xmin)*(x1-x0)
        yp=lambda v:y1-(v-ymin)/(ymax-ymin)*(y1-y0)
        for tick in np.arange(ymin,ymax+step/2,step):
            y=yp(tick);line(x0,y,x1,y)
            val=f'{tick/1000:g}k' if abs(tick)>=1000 else f'{tick:g}'
            text(xx+1,y+2.4,val,7.3)
        for tick in np.arange(xmin,xmax+.01,4 if xmax-xmin>12 else 2):
            text(xp(tick)-3,y1+11,f'{tick:g}',7.3)
        line(x0,y1,x1,y1,'#728995',.6)
        if p['one']:line(x0,yp(1),x1,yp(1),'#83949d',.6,(2,2))
        if p['endpoint'] is not None:
            xe=xp(p['endpoint']);line(xe,y0,xe,y1,'#8b989f',.6,(1,2))
        for t,v,lab,color,lw,dash in lines:
            pathline=cv.beginPath();pathline.moveTo(xp(t[0]),height-yp(v[0]))
            for tx,vy in zip(t[1:],v[1:]):pathline.lineTo(xp(tx),height-yp(vy))
            cv.setStrokeColor(HexColor(color));cv.setLineWidth(lw);cv.setDash(dash);cv.drawPath(pathline)
        if idx//2==rows-1:
            text(xx+65,y1+23,'Acquisition time (h)',7.6)
    cv.showPage();cv.save()
    d=pypdfium2.PdfDocument(path)
    d[0].render(scale=5).to_pil().save(path.with_suffix('.png'),dpi=(360,360));d.close()
    FIGURES[label]={'path':str(path.relative_to(ROOT)),'png':str(path.with_suffix('.png').relative_to(ROOT)),
                    'width_pt':width,'height_pt':height,'title':title,'panels':len(panels)}

draw('7','Distinct repression trajectories',[
 panel('Baseline guides','Fold repression (N/P)',[curve('may12',k,'NP_norm',k,COLORS[j]) for j,k in enumerate(['2A','4A'])],10,one=True),
 panel('Fusion batch 1','Fold repression (N/P)',[curve('jun08',k,'NP_norm',lab,COLORS[j]) for j,(k,lab) in enumerate([('088','dTasR'),('132','N-GS15'),('136','N-Rigid10'),('142','C-Rigid5')])],15,one=True),
 panel('Fusion batch 2','Fold repression (N/P)',[curve('jun11',k,'NP_norm',lab,COLORS[j]) for j,(k,lab) in enumerate([('088','dTasR'),('137','N-Rigid20'),('140','C-GS10')])],14,one=True),
 panel('N-Rigid20 growth','OD600',component('jun11','137','OD'),14),
 panel('N-Rigid20 fluorescence','GFP fluorescence (a.u.)',component('jun11','137','FL'),14),
 panel('N-Rigid20 normalized signal','GFP / OD600 (a.u.)',component('jun11','137','Y'),14),
])

def paired_components(items):
    out=[]
    for metric,unit,desc in [('OD','OD600','growth'),('FL','GFP fluorescence (a.u.)','fluorescence'),('Y','GFP / OD600 (a.u.)','normalized')]:
        for pid,key,lab,ep in items:
            out.append(panel(lab+' '+desc,unit,component(pid,key,metric),ep))
    return out

draw('D1','Signal components of contrasting TadA8e fusions',paired_components([
 ('jun08','132','N-GS15',15),('jun08','142','C-Rigid5',15)]))
draw('D2','Signal components of native and BoxB configurations',paired_components([
 ('may29','native 2A','Native 2A',10),('may29','BoxB 2A','BoxB 2A',10)]))
draw('D3','Time dependence of matched-site repression and non-targeting controls',[
 panel('Matched site T7','NT-corrected repression (%)',[curve('jul21i',k,'repression_nt_percent',lab,COLORS[j]) for j,(k,lab) in enumerate([('088 / 165 (T7)','dTasR'),('164 / 161 (T7)','dSpyCas9')])],10),
 panel('Matched site T8','NT-corrected repression (%)',[curve('jul21i',k,'repression_nt_percent',lab,COLORS[j]) for j,(k,lab) in enumerate([('088 / 166 (T8)','dTasR'),('164 / 162 (T8)','dSpyCas9')])],10),
 panel('NT responses','FL/OD600 P/N',[curve('jul21i',k,'PN_norm',lab,COLORS[j]) for j,(k,lab) in enumerate([('088 / 168 (NT)','dTasR NT'),('164 / 169 (NT)','dSpyCas9 NT')])],10,one=True),
 panel('BoxB comparison','Fold repression (N/P)',[curve('may29',k,'NP_norm',lab,COLORS[j]) for j,(k,lab) in enumerate([('native 2A','Native 2A'),('BoxB 2A','BoxB 2A'),('native 3A','Native 3A'),('BoxB 3A','BoxB 3A')])],10,one=True),
])
(QA/'figures.json').write_text(json.dumps(FIGURES,indent=2),encoding='utf-8')
print('Created',len(FIGURES),'figures')
