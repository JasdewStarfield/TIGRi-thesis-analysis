import csv
from collections import defaultdict
from statistics import mean, stdev
from math import ceil
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pypdfium2 as pdf
from config import OUT, FONT_REGULAR, FONT_BOLD
q=OUT; out=q/'figures'
out.mkdir(exist_ok=True);q.mkdir(exist_ok=True)
for f,name in [(FONT_REGULAR,'Chart'),(FONT_BOLD,'ChartBold')]:pdfmetrics.registerFont(TTFont(name,str(f)))
# Use full-precision values regenerated from the source workbooks, not rounded labels.
plates=defaultdict(lambda:defaultdict(lambda:{'N':[],'P':[]}))
with (OUT/'endpoint_wells.csv').open(encoding='utf-8-sig',newline='') as stream:
 for row in csv.DictReader(stream):
  plates[int(row['audit_index'])][row['group']][row['condition']].append(float(row['fluorescence_per_od']))
for plate in plates.values():
 for values in plate.values():
  assert all(len(values[c])==3 for c in ['N','P'])
dark='#172c37';muted='#47606b';grid='#d7e2e6';blue='#246384';orange='#ae521e'
W=502
def ink(color):return HexColor(color)
def txt(x,y,s,size=10,align='left',color=dark,bold=False):
 cv.setFillColor(ink(color));cv.setFont('ChartBold' if bold else 'Chart',size);getattr(cv,{'left':'drawString','center':'drawCentredString','right':'drawRightString'}[align])(x,H-y,str(s))
def line(x,y,x2,y2,color=grid,lw=.65):
 cv.setStrokeColor(ink(color));cv.setLineWidth(lw);cv.line(x,H-y,x2,H-y2)
def group(i,keys=None,labels=None):
 keys=list(plates[i]) if keys is None else keys
 return [(lab,plates[i][k]) for lab,k in zip(labels or keys,keys)]
def ratio(d):return mean(d['P'])/mean(d['N'])
teal='#09A3B1';cream='#F0DFA9';black='#161616'
def swatch(x,y,color,label):
 cv.setFillColor(ink(color));cv.rect(x,H-y,13,7,stroke=0,fill=1);txt(x+17,y,label,10,color=black)
def legend():
 if n!=4:
  swatch(367,16,teal,'−aTc');swatch(429,16,cream,'+aTc')

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

def frame(top,bottom,highest,steps,axis):
 # Boxed, zero-based axes and outward ticks follow the original progress-report figures.
 x0,x1=64,W-10;cv.setStrokeColor(ink(black));cv.setLineWidth(.75);cv.rect(x0,H-bottom,x1-x0,bottom-top,stroke=1,fill=0)
 for v in range(0,int(highest)+1,int(steps)):
  y=bottom-v/highest*(bottom-top);line(x0-3,y,x0,y,black,.65);txt(x0-6,y+3,str(v),8.5,'right',black)
 cv.saveState();cv.translate(13,H-(top+bottom)/2);cv.rotate(90);cv.setFillColor(ink(black));cv.setFont('Chart',9);notation_label(cv,0,0,axis,'Chart',9,center=True);cv.restoreState()
 return x0,x1
def panel(top,title,data,step,unit,scale=1,plotheight=88):
 txt(5,top,title,11.6,bold=True,color=black)
 step=int(step*scale);y0=top+12;y1=y0+plotheight
 high=max(max(v) if n==4 else mean(v)+stdev(v) for _,d in data for v in d.values())
 high=max(high,max(mean(v)+stdev(v) for _,d in data for v in d.values()))
 ymax=ceil(high/(1-16/plotheight)/step)*step
 x0,x1=frame(y0,y1,ymax,step,unit.replace('×10³ ',''))
 dy=lambda v:y1-v/ymax*plotheight
 width=(x1-x0)/len(data);bw=min(48,width*.34)
 for idx,(lab,d) in enumerate(data):
  xc=x0+(idx+.5)*width
  for cond,sign,col in [('N',-1,teal),('P',1,cream)]:
   mu=mean(d[cond]);sd=stdev(d[cond]);x=xc+sign*bw*.5
   cv.setFillColor(ink(col));cv.rect(x-bw/2,H-y1,bw,y1-dy(mu),stroke=0,fill=1)
   line(x,dy(mu),x,dy(mu+sd),black,.68);line(x-2.1,dy(mu+sd),x+2.1,dy(mu+sd),black,.68)
   if n==4:
    for j,val in enumerate(d[cond]):
     cv.setStrokeColor(ink(black));cv.setFillColor(ink('#FFFFFF'));cv.setLineWidth(.6)
     cv.circle(x+(j-1)*2.8,H-dy(val),1.5,stroke=1,fill=1)
  topv=max(mean(v)+stdev(v) for v in d.values())
  if n==4:topv=max(topv,max(max(v) for v in d.values()))
  y=dy(topv)-3;line(xc-bw*.52,y,xc+bw*.52,y,black,.6)
  txt(xc,y-2.4,f'{1/ratio(d):.2f}×',8.3,'center',black)
  if n in (3,6):
   # Slanted names retain the slide convention and keep long linker names legible.
   cv.saveState();cv.translate(xc+3,H-y1-6);cv.rotate(38);cv.setFillColor(ink(black));cv.setFont('Chart',8.7);cv.drawRightString(0,0,('tig'+lab if n==3 else lab));cv.restoreState()
  else:
   for j,part in enumerate(lab.split('\n')):txt(xc,y1+12+10*j,part,9,'center',black)
 line(x0,y1,x1,y1,black,.7)
 if n==4:swatch(363,top,teal,'−aTc');swatch(429,top,cream,'+aTc')
def score(top):
 txt(5,top,'A   Matched sites · 10 h',11.6,bold=True,color=black)
 swatch(329,top,'#4C6572','dTasR');swatch(407,top,'#B5C4CB','dSpyCas9')
 y0=top+12;y1=y0+82;frame(y0,y1,100,25,'Corrected repression (%)')
 for j,site in enumerate(['T7','T8','T9']):
  xc=64+(j+.5)*(W-74)/3;bw=31
  for eff,sign,col in [('088',-1,'#4C6572'),('164',1,'#B5C4CB')]:
   subset=plates[9];selected=lambda s:next(v for k,v in subset.items() if k.startswith(eff) and k.endswith('('+s+')'))
   v=100*(1-ratio(selected(site))/ratio(selected('NT')));x=xc+sign*bw*.5
   cv.setFillColor(ink(col));cv.rect(x-bw/2,H-y1,bw,v*.82,fill=1,stroke=0);txt(x,y1-v*.82-4,f'{v:.0f}%',9,'center',black)
  txt(xc,y1+13,site,9,'center',black)
 line(64,y1,W-10,y1,black,.7)

labels3=['dTasR','N-GS15','N-GS10','N-GS5','N-Rigid10','C-Rigid5','C-GEG15']
labels4=['dTasR','N-Rigid20','N-GEG15','N-GGEGG25','C-GS10','C-GS20','C-Rigid15','C-GGEGG25']
# BioRender schematics (Figures 1, 2, 3A and 4A) are separate artwork.
# These exports contain only the quantitative panels generated by this pipeline.
for n,H,slug in [(3,202,'Figure-3B-guide-repression'),(4,345,'Figure-4BC-matched-sites-and-controls'),
                 (5,201,'Figure-5-boxb-repression'),(6,365,'Figure-6-tada8e-fusions')]:
 base=out/slug;vp=base.with_suffix('.pdf')
 cv=canvas.Canvas(str(vp),pagesize=(W,H));cv.setTitle(slug);legend()
 if n==3:
  panel(35,'B   Repression across guide orientations · 10 h',group(0),5,'GFP/OD600 (a.u.)',scale=1000,plotheight=105)
 if n==4:
  score(35)
  keys=[e+' NT'+str(i) for e in ('088','164') for i in range(1,5)]
  labels=[('dTasR' if k.startswith('088') else 'dSpyCas9')+'\n'+k.split()[1] for k in keys]
  panel(168,'B   Non-targeting guide panel · 10 h',group(11,keys,labels),5,'GFP/OD600 (a.u.)',scale=1000)
  # Preserve the exact lettering overlay used when the schematic became panel A.
  # Keeping the original title positions also avoids a kerning shift after relabeling.
  for letter,y in [('B',35),('C',168)]:
   cv.setFillColor(ink('#FFFFFF'));cv.rect(3,H-(y-13)-16,15,16,stroke=0,fill=1)
   txt(5,y,letter,11.6,bold=True,color=black)
 if n==5:
  panel(35,'BoxB guide comparison · 29 May · 10 h',group(2,labels=['Native 1B','Native 2A','Native 3A','BoxB 2A','BoxB 3A']),10,'GFP/OD600 (a.u.)',scale=1000)
 if n==6:
  panel(35,'A   Fusion screen, batch 1 · ≈15 h',group(3,labels=labels3),10,'GFP/OD600 (a.u.)',scale=1000)
  panel(203,'B   Fusion screen, batch 2 · 14 h',group(4,labels=labels4),10,'GFP/OD600 (a.u.)',scale=1000)
 cv.showPage();cv.save()
 document=pdf.PdfDocument(vp)
 document[0].render(scale=5).to_pil().save(base.with_suffix('.png'),dpi=(360,360))
 document.close()
