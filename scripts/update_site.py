"""Rebuild static current indicators and real dated snapshots from data/polls.json.

Run from repository root: python scripts/update_site.py
No network, interpolated data, imputation, or runtime data loading.
"""
import json, math, re
from datetime import date
from html import escape
from pathlib import Path

PARTIES = dict(zip('fdi pd m5s fn fi avs lega azione iv europa nm'.split(),
    ['Fratelli d’Italia','Partito Democratico','Movimento 5 Stelle','Futuro Nazionale',
     'Forza Italia','Alleanza Verdi e Sinistra','Lega','Azione','Italia Viva','+Europa','Noi Moderati']))
NAMES = {'swg':'SWG','ipsos':'Ipsos Doxa','quorum':'Quorum–YouTrend','piepoli':'Istituto Piepoli',
         'only':'Only Numbers','emg':'EMG Different','eumetra':'Eumetra','termometro':'Termometro Politico',
         'tecne':'Tecnè','bidimedia':'BiDiMedia','winpoll':'Winpoll','noto':'Noto','ixe':'Ixè'}
LEFT = ['pd','m5s','avs','iv','europa']
RIGHT = ['fdi','lega','fn','fi','nm']
ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT/'data/polls.json').read_text())
polls = data['polls']
assert len({p['id'] for p in polls}) == len(polls)
for p in polls:
    date.fromisoformat(p['published'])
    assert all(k in PARTIES and isinstance(v,(int,float)) and 0<=v<=100 for k,v in p['values'].items()), p['id']
    assert sum(p['values'].values()) <= 100.2, p['id']
    assert p['source'] is None or p['source'].startswith('https://')

def snapshot(day):
    d = date.fromisoformat(day)
    latest = {}
    for p in sorted(polls,key=lambda p:(p['published'],p['id'])):
        age = (d-date.fromisoformat(p['published'])).days
        if p['comparable'] and 0<=age<=42:
            latest[p['institute']] = p
    weights = {k:math.exp(-(d-date.fromisoformat(p['published'])).days/21) for k,p in latest.items()}
    means, coverage, shares = {}, {}, {}
    for party in PARTIES:
        keys = [k for k,p in latest.items() if party in p['values']]
        if not keys: continue
        total = sum(weights[k] for k in keys)
        means[party] = sum(weights[k]*latest[k]['values'][party] for k in keys)/total
        coverage[party] = [latest[k]['id'] for k in keys]
        shares[party] = max(weights[k]/total for k in keys)
    valid = all(len(coverage.get(k,[]))>=3 and shares.get(k,1)<=.6 for k in PARTIES)
    return {'date':day,'parties':means,'coverage':coverage,'max_weight_share':shares,
            'selected_polls':[p['id'] for p in latest.values()], 'valid':valid,
            'left':sum(means.get(k,0) for k in LEFT), 'right':sum(means.get(k,0) for k in RIGHT)}

as_of = max(p['published'] for p in polls if p['comparable'])
current = snapshot(as_of)
assert current['valid']
series = [snapshot(d) for d in sorted({p['published'] for p in polls if p['comparable']}) if d>='2026-09-03']
series = [s for s in series if s['valid']]
assert series[-1] == current
derived = {'method':'v1','date_basis':'publication','tau_days':21,'lookback_days':42,
           'one_poll_per_institute':True,'current':current,'snapshots':series}
(ROOT/'data/derived.json').write_text(json.dumps(derived,ensure_ascii=False,indent=2)+'\n')
def fmt(v): return f'{v:.2f}'.replace('.',',')
def dt(s):
    d = date.fromisoformat(s)
    return f'{d.day} settembre {d.year}' if d.month==9 else d.strftime('%d/%m/%Y')
def card(content): return '<section class="card">'+content+'</section>'
means = current['parties']; left=current['left']; right=current['right']; remainder=100-left-right
intro = card(f'<div class="kicker">Media VOTO27 • {dt(as_of)}</div><h1>Oggi</h1>'
    f'<p class="sub">Ultima rilevazione comparabile per ciascuno dei {len(current["selected_polls"])} istituti nella finestra di 42 giorni. Peso exp(−giorni/21). Ogni partito utilizza soltanto valori disponibili.</p>'
    f'<div class="soft-stat-grid"><div class="soft-stat blue"><div class="lab">Primo partito</div><div class="stat-name">Fratelli d’Italia</div><div class="num">{fmt(means["fdi"])}%</div></div>'
    f'<div class="soft-stat warm"><div class="lab">Data effettiva della media</div><div class="stat-name">Ultimo dato incluso</div><div class="num">{date.fromisoformat(as_of).day} set</div></div></div>'
    f'<p class="tiny">Verifica delle fonti e aggiornamento delle schede: {dt(data["verified_on"])}. La data corrente nell’intestazione non è la data delle medie.</p>')
pole = '<div class="kicker">Scenario bipolare VOTO27</div><h2>Rapporto tra i due poli</h2><p class="sub">Somma delle medie per partito. Copertura diversa tra partiti: non è un quesito sulle coalizioni né una previsione elettorale.</p><div class="poles-summary">'
for name, keys, value, cls in [('Sinistra / centrosinistra',LEFT,left,'left'),('Destra / centrodestra',RIGHT,right,'right')]:
    pole += f'<div class="pole-box pole-{cls}"><span class="pole-label">{name}</span><strong>{fmt(value)}%</strong><div class="pole-members">'+ ' · '.join(PARTIES[k] for k in keys)+'</div></div>'
pole += f'</div><div class="balance"><div class="balance-left" style="width:{100*left/(left+right):.2f}%"></div><div class="balance-right" style="width:{100*right/(left+right):.2f}%"></div></div><div class="balance-labels"><span>{fmt(left)}%</span><span>distacco {fmt(abs(right-left))} punti</span><span>{fmt(right)}%</span></div>'
pole += f'<div class="unassigned-chip"><span>Residuo non assegnato</span><strong>{fmt(remainder)}%</strong></div><p class="pole-note">Residuo aritmetico 100 meno i poli, non una media autonoma di “Altri”. Include Azione ({fmt(means["azione"])}%) e liste non attribuite. Nessuna conversione di indecisi o non risposta in astensione.</p>'
intents = f'<div class="kicker">Media ponderata</div><h2>Intenzioni di voto</h2><time datetime="{as_of}">{dt(as_of)}</time>'
for k,v in sorted(means.items(),key=lambda x:-x[1]):
    names = ', '.join(NAMES[p['institute']] for p in polls if p['id'] in current['coverage'][k])
    intents += f'<details class="party party-{k}"><summary><div class="prow"><span class="pname"><i class="party-dot"></i>{PARTIES[k]}</span><b>{fmt(v)}%</b></div><div class="bar"><div class="fill" style="width:{v/35*100:.2f}%"></div></div></summary><div class="party-detail">Copertura: {len(current["coverage"][k])} istituti. {escape(names)}. Peso massimo di un istituto: {fmt(current["max_weight_share"][k]*100)}%.</div></details>'
intents += '<p class="tiny">Le quote non vengono rinormalizzate per colmare valori mancanti. Se l’ultima scheda di un istituto omette un partito, non si recupera il suo valore da una scheda precedente.</p>'

recent = f'<div class="kicker">Schede aggiornate • {dt(data["verified_on"])}</div><h2>Rilevazioni recenti</h2>'
selected = set(current['selected_polls'])
for p in sorted((p for p in polls if p['source']),key=lambda p:(p['published'],p['id']),reverse=True):
    vals = ' · '.join(f'{PARTIES[k]} {str(v).replace(".",",")}%' for k,v in p['values'].items())
    missing = ', '.join(PARTIES[k] for k in PARTIES if k not in p['values']) or 'nessuno tra gli 11 partiti mostrati'
    period = ' – '.join(dt(x) for x in p['fieldwork']) if p['fieldwork'] else 'non verificato'
    recent += f'<details class="verified-poll" data-institute="{p["institute"]}"><summary><b>{NAMES[p["institute"]]} · {dt(p["published"])}</b><br><span>{"Incluso nei valori disponibili" if p["id"] in selected else "Superato nella media corrente"}</span></summary><p>{vals}</p><p class="tiny">Interviste: {period}. Metodo: {p["method"] or "non verificato"}. Campione: {p["sample"] or "non verificato"}. Partiti mancanti: {missing}.</p>'
    recent += f'<p class="tiny">{escape(p["note"])}</p><p><a href="{escape(p["source"],quote=True)}" target="_blank" rel="noopener noreferrer">Fonte: {escape(p["source_kind"])} ↗</a></p>'
    for link,label in [('primary_source','Programma originale'),('corroborating_source','Riscontro e dettaglio dei valori')]:
        if p.get(link): recent += f'<p><a href="{p[link]}" target="_blank" rel="noopener noreferrer">{label} ↗</a></p>'
    for key in ['turnout','nonresponse']:
        if p.get(key): recent += f'<p class="tiny">{escape(p[key]["label"])}: {p[key]["value"]}%. Categoria originale, mantenuta separata.</p>'
    recent += '</details>'
recent += '<p class="tiny">Registro ufficiale sondaggipoliticoelettorali.it non consultabile nel controllo del 30 settembre. I valori verificati nelle fonti disponibili restano utilizzabili; i metadati mancanti restano espliciti.</p>'
baseline = series[0]
movement = card(f'<div class="kicker">Movimento • {dt(baseline["date"])} – {dt(as_of)}</div><h2>Variazione dello scenario</h2><p>Centrosinistra: {fmt(left-baseline["left"])} punti. Centrodestra: {fmt(right-baseline["right"])} punti.</p><p class="tiny">Confronto fra due snapshot reali; la composizione degli istituti cambia nel periodo. Il confronto trimestrale non viene esteso senza i dati storici necessari.</p>')
today = '<main id="oggi" class="page">'+intro+card(pole)+card(intents)+'<section class="card" id="rilevazioni-recenti">'+recent+'</section>'+movement+'</main>'

def chart(keys,labels,colors,low,high):
    width,height=640,280
    start=date.fromisoformat(series[0]['date']); end=date.fromisoformat(as_of)
    def x(s): return 48+550*(date.fromisoformat(s['date'])-start).days/max(1,(end-start).days)
    def y(v): return 225-185*(v-low)/(high-low)
    svg=f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Medie ponderate, punti reali dal {dt(series[0]["date"])} al {dt(as_of)}" style="width:100%;background:#fff;color:#233044">'
    for v in range(low,high+1,5):
        svg+=f'<line x1="48" x2="600" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#d5dbe3"/><text x="6" y="{y(v)+4:.1f}" fill="#233044" font-size="14">{v}%</text>'
    for key,label,color in zip(keys,labels,colors):
        values=[s[key] if key in ['left','right'] else s['parties'][key] for s in series]
        points=' '.join(f'{x(s):.1f},{y(v):.1f}' for s,v in zip(series,values))
        svg+=f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>'
        for s,v in zip(series,values):
            svg+=f'<circle cx="{x(s):.1f}" cy="{y(v):.1f}" r="3" fill="{color}"><title>{dt(s["date"])} · {label}: {fmt(v)}%</title></circle>'
    svg+=f'<text x="48" y="258" fill="#233044" font-size="14">{start.day} settembre</text><text x="515" y="258" fill="#233044" font-size="14">{end.day} settembre</text></svg>'
    return svg+'<p>'+ ' · '.join(f'{label}: {fmt(current[key] if key in ["left","right"] else means[key])}%' for key,label in zip(keys,labels))+'</p>'
trend = '<main id="trend" class="page">'+card(f'<div class="kicker">Snapshot v1 • {dt(as_of)}</div><h1>Trend</h1><p class="sub">Un punto per ogni data con nuovi dati disponibili; una sola rilevazione per istituto nei 42 giorni precedenti. Le linee collegano snapshot, non stime giornaliere.</p>')
trend += card('<h2>I due poli</h2>'+chart(['left','right'],['Centrosinistra','Centrodestra'],['#1e5aaa','#aa3d18'],40,55))
trend += card('<h2>Primi tre partiti</h2>'+chart(['fdi','pd','m5s'],['FdI','PD','M5S'],['#203c66','#a51f43','#725100'],10,30))
trend += card('<h2>FN, FI, AVS e Lega</h2>'+chart(['fn','fi','avs','lega'],['Futuro Nazionale','Forza Italia','AVS','Lega'],['#633a90','#174f98','#286437','#9b3b17'],0,10))
trend += card('<h2>Altri partiti rilevati</h2>'+chart(['azione','iv','europa','nm'],['Azione','Italia Viva','+Europa','Noi Moderati'],['#633a90','#174f98','#286437','#9b3b17'],0,5))
trend += card('<h2>Snapshot verificabili</h2><div style="overflow-x:auto"><table><thead><tr><th>Data</th><th>Istituti</th><th>CSX</th><th>CDX</th></tr></thead><tbody>'+''.join(f'<tr><td>{dt(s["date"])}</td><td>{len(s["selected_polls"])}</td><td>{fmt(s["left"])}%</td><td>{fmt(s["right"])}%</td></tr>' for s in series)+'</tbody></table></div><p class="tiny">Storico precedente: i grafici della versione del 15 settembre sono conservati nel repository, ma non prolungati perché mancano nel feed i dati di origine per ricostruirli. Nessun punto fittizio è aggiunto. Ogni punto pubblicato supera la soglia di almeno tre istituti e nessuno oltre il 60% per ogni partito.</p>')+'</main>'

h=(ROOT/'index.html').read_text()
for key,value in [('oggi',today),('trend',trend)]:
    h,n=re.subn(r'<main id="'+key+r'".*?</main>',lambda m:value,h,flags=re.S); assert n==1
# Update the index labels; older cards remain identifiable as dated archive records.
h=h.replace('nuova rilevazione, fuori media corrente','valori verificati inclusi nella media')
h=h.replace('21/09/2026 · valori verificati inclusi nella media','21/09/2026 · superato da SWG del 28 settembre')
h=h.replace('Ogni scheda qui sotto viene generata automaticamente dal database.','Archivio delle schede. Le rilevazioni recenti e la copertura corrente sono riportate in Oggi.')
link='<label class="poll-link" for="tab-oggi"><div><b>Ultime rilevazioni verificate</b><span>SWG 28/09 · Ipsos 26/09 · Piepoli e TP 25/09 · Quorum, EMG ed Eumetra 24/09</span></div><strong>›</strong></label>'
h=h.replace('<h1>Sondaggi</h1>','<h1>Sondaggi</h1>'+link) if link not in h else h
h=h.replace('Per gli snapshot storici viene usata una finestra massima di 42 giorni.','Per medie correnti e snapshot storici viene usata una finestra massima di 42 giorni con una sola rilevazione per istituto, indipendentemente dalla frequenza di pubblicazione. Le date di pubblicazione sono la base temporale uniforme di questo feed; le date delle interviste restano separate.')
h=re.sub(r'(<h3>3\. Media per partito</h3>\s*)<p>.*?</p>',r'\1<p>Per ciascun partito calcoliamo separatamente la media ponderata delle rilevazioni in cui quel partito è effettivamente presente. Non assegniamo valori inventati alle liste non testate. Metodo o campione mancanti non escludono da soli valori nazionali comparabili e verificati, purché istituto e data siano identificabili. La copertura è indicata per partito.</p>',h,flags=re.S)
h=re.sub(r'<section class="card method-card">\s*<h3>6\..*?</section>',card('<h3>6. Limiti del modello</h3><p>Le correzioni per differenze sistematiche tra istituti non sono applicate. Lo storico visualizzato copre soltanto snapshot ricostruibili dal feed disponibile: eventuali lacune restano esplicite.</p>'),h,flags=re.S)
h=re.sub(r'<section class="card method-card">\s*<h3>8\..*?</section>',card('<h3>8. Controllo qualità</h3><p>Ogni punto del grafico richiede almeno tre istituti e nessun istituto oltre il 60% del peso per ciascun partito. Le rilevazioni di uno stesso istituto, incluso Only Numbers / Realpolitik, non si duplicano.</p>'),h,flags=re.S)
h=re.sub(r'<section class="card method-card"><h3>9\..*?</section>',card('<h3>9. Stato del metodo</h3><p>Metodo v1: medie per partito, ponderazione temporale e copertura dichiarata. I dati storici anteriori alla serie ricostruibile non sono estesi artificialmente.</p>'),h,flags=re.S)
h=h.replace('PASS</b> (17 sondaggi)',f'PASS</b> ({len(polls)} sondaggi nel feed)')
h=h.replace('Rilevazione individuata ma tabella completa non disponibile: esclusa dalla media corrente.','Scheda storica parziale, superata dalla pubblicazione verificata del 24 settembre riportata in Oggi.')
config=json.loads((ROOT/'data/config.json').read_text())
config.update(data_last_update=as_of,sources_verified_on=data['verified_on'],cards_updated_on=data['verified_on'])
config['aggregation'].update(current_lookback_days=42,current_one_poll_per_institute=True,date_basis='publication')
(ROOT/'data/config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
h=re.sub(r'const CONFIG = .*?;',lambda m:'const CONFIG = '+json.dumps(config,ensure_ascii=False)+';',h)
style='\n<style id="verified-data-style">.verified-poll{margin:14px 0;padding:14px;background:linear-gradient(120deg,var(--poll-bg,#edf6fc),#fffaf3);color:#233044;border:1px solid #bfd4e2;border-left:4px solid var(--poll-accent,#79aec9);border-radius:14px}.verified-poll summary{cursor:pointer}.verified-poll summary,.verified-poll summary b,.verified-poll p,.verified-poll .tiny{color:#233044 !important}.verified-poll summary b{color:var(--poll-ink,#244d75) !important}.verified-poll summary span{color:#3d665e;font-size:12px;font-weight:650}.verified-poll a{color:#174f98 !important;text-decoration:underline}#trend table{width:100%;border-collapse:collapse}#trend td,#trend th{padding:9px;text-align:left;border-bottom:1px solid #d5dbe3}</style>\n'
# Harmonized pastel identities, with dark readable institute names.
PALETTE = {
    'swg': ('eaf3fc','79a9d1','244d75'),
    'ipsos': ('f1edfa','ad98cc','594174'),
    'termometro': ('fff3da','d6b264','72551f'),
    'piepoli': ('edf4e7','a0b885','425d32'),
    'quorum': ('e5f5f1','7eb8ac','285e55'),
    'eumetra': ('fbecef','d09caa','783f51'),
    'emg': ('fff0e6','d6a182','78472c'),
    'only': ('eef0fc','97a4ce','414f7b'),
    'ixe': ('f4ecf5','ba96bf','67446d'),
}
palette_css = ''.join('.verified-poll[data-institute="'+key+'"]{--poll-bg:#'+bg+';--poll-accent:#'+accent+';--poll-ink:#'+ink+'}' for key,(bg,accent,ink) in PALETTE.items())
style=style.replace('</style>',palette_css+'</style>')
if 'id="verified-data-style"' in h:
    h=re.sub(r'<style id="verified-data-style">.*?</style>',lambda m:style.strip(),h,flags=re.S)
else:
    h=h.replace('</head>',style+'</head>')
ids=re.findall(r'\bid="([^"]+)"',h); assert len(ids)==len(set(ids))
assert 'ricalcolo della serie e dei grafici è in corso' not in h
(ROOT/'index.html').write_text(h)
print(json.dumps({'as_of':as_of,'means':means,'left':left,'right':right,'polls':len(polls),'institutes':len(current['selected_polls']),'snapshots':len(series)},ensure_ascii=False,indent=2))
