"""Rebuild static current indicators and real dated snapshots from data/polls.json.

Run from repository root: python scripts/update_site.py
No network, interpolated data, imputation, or runtime data loading.
"""
import hashlib, json, math, re
from datetime import date
from html import escape
from pathlib import Path

PARTIES = dict(zip('fdi pd m5s fn fi avs lega azione iv europa nm'.split(),
    ['Fratelli d’Italia','Partito Democratico','Movimento 5 Stelle','Futuro Nazionale',
     'Forza Italia','Alleanza Verdi e Sinistra','Lega','Azione','Italia Viva','+Europa','Noi Moderati']))
NAMES = {'swg':'SWG','ipsos':'Ipsos Doxa','quorum':'Quorum–YouTrend','piepoli':'Istituto Piepoli',
         'only':'Only Numbers','emg':'EMG Different','eumetra':'Eumetra','termometro':'Termometro Politico',
         'tecne':'Tecnè','bidimedia':'BiDiMedia','winpoll':'Winpoll','noto':'Noto','ixe':'Ixè',
         'cluster17':'Cluster17','lab21':'Lab21','piave':'Piave'}
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
MONTHS = ['gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto',
          'settembre','ottobre','novembre','dicembre']
def dt(s):
    d = date.fromisoformat(s)
    return f'{d.day} {MONTHS[d.month-1]} {d.year}'
def short_dt(s):
    d = date.fromisoformat(s)
    return f'{d.day} {MONTHS[d.month-1][:3]}'
def card(content): return '<section class="card">'+content+'</section>'
means = current['parties']; left=current['left']; right=current['right']; remainder=100-left-right
intro = card(f'<div class="kicker">Media VOTO27 • {dt(as_of)}</div><h1>Oggi</h1>'
    f'<p class="sub">Ultima rilevazione comparabile per ciascuno dei {len(current["selected_polls"])} istituti nella finestra di 42 giorni. Peso exp(−giorni/21). Ogni partito utilizza soltanto valori disponibili.</p>'
    f'<div class="soft-stat-grid"><div class="soft-stat blue"><div class="lab">Primo partito</div><div class="stat-name">Fratelli d’Italia</div><div class="num">{fmt(means["fdi"])}%</div></div>'
    f'<div class="soft-stat warm"><div class="lab">Data effettiva della media</div><div class="stat-name">Ultimo dato incluso</div><div class="num">{short_dt(as_of)}</div></div></div>'
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
def status(p):
    if not p['comparable']: return 'Fuori media: '+p.get('exclusion_reason','categorie non comparabili')
    if p['id'] in selected: return 'Incluso nei valori disponibili'
    age=(date.fromisoformat(as_of)-date.fromisoformat(p['published'])).days
    return 'Fuori finestra di 42 giorni' if age>42 else 'Superato nella media corrente'
def metadata(p):
    period = ' – '.join(dt(x) for x in p['fieldwork']) if p['fieldwork'] else 'non verificato'
    missing = ', '.join(PARTIES[k] for k in PARTIES if k not in p['values']) or 'nessuno tra gli 11 partiti mostrati'
    result=f'<p class="tiny">Interviste: {period}. Metodo: {escape(p["method"] or "non verificato")}. Campione: {p["sample"] or "non verificato"}. Partiti mancanti: {missing}.</p>'
    if p.get('metadata_origin'):
        result+=f'<p class="tiny">{escape(p["metadata_origin"])}</p>'
        if p.get('archive_metadata'):
            result+=f'<p class="tiny">Testo della scheda storica: {escape(p["archive_metadata"])}</p>'
    if p.get('extra_values'):
        result+='<p class="tiny">Altre categorie originali, separate dalle medie: '+escape(' · '.join(f'{k}: {str(v).replace(".",",")}%' for k,v in p['extra_values'].items()))+'.</p>'
    if p.get('note'): result+=f'<p class="tiny">{escape(p["note"])}</p>'
    if p.get('source'):
        result+=f'<p><a href="{escape(p["source"],quote=True)}" target="_blank" rel="noopener noreferrer">Fonte: {escape(p["source_kind"])} ↗</a></p>'
    else:
        result+='<p class="tiny">Dati ereditati dall’archivio VOTO27; fonte originale non conservata, non nuovamente verificati.</p>'
    for link,label in [('primary_source','Fonte originale'),('corroborating_source','Riscontro dei valori')]:
        if p.get(link): result+=f'<p><a href="{escape(p[link],quote=True)}" target="_blank" rel="noopener noreferrer">{label} ↗</a></p>'
    for key in ['turnout','nonresponse']:
        if p.get(key): result+=f'<p class="tiny">{escape(p[key]["label"])}: {str(p[key]["value"]).replace(".",",")}%. Categoria originale, mantenuta separata.</p>'
    return result
for p in sorted((p for p in polls if p['source'] or p['id'] in selected),key=lambda p:(p['published'],p['id']),reverse=True):
    vals = ' · '.join(f'{PARTIES[k]} {str(v).replace(".",",")}%' for k,v in p['values'].items())
    recent += f'<details class="verified-poll" data-institute="{p["institute"]}"><summary><b>{NAMES[p["institute"]]} · {dt(p["published"])}</b><br><span>{escape(status(p))}</span></summary><p>{vals}</p>'+metadata(p)+'</details>'
recent += '<p class="tiny">'+escape(data.get('verification_note','Fonti e copertura dichiarate per ciascuna scheda; i metadati non verificati restano espliciti.'))+'</p>'
baseline = series[0]
movement = card(f'<div class="kicker">Movimento • {dt(baseline["date"])} – {dt(as_of)}</div><h2>Variazione dello scenario</h2><p>Centrosinistra: {fmt(left-baseline["left"])} punti. Centrodestra: {fmt(right-baseline["right"])} punti.</p><p class="tiny">Confronto fra due snapshot reali; la composizione degli istituti cambia nel periodo. Il confronto trimestrale non viene esteso senza i dati storici necessari.</p>')
pole += "<p class=\"pole-note\" id=\"scn-alliance-note\"><b>Sud chiama Nord — Cateno De Luca:</b> collocato nel quadro politico del centrodestra nazionale dopo l’accordo per le politiche 2027 annunciato da De Luca il 9 ottobre 2026. L’intesa non si estende automaticamente alla Sicilia. Nei sondaggi del feed non è disponibile un valore separato verificato: nessuna percentuale aggiunta ai poli e nessuna modifica allo storico. L’1,5% dichiarato dal leader non è utilizzato come sondaggio. <a href=\"https://www.ilfoglio.it/politica/2026/10/09/news/fratelli-di-cateno-correro-con-meloni-per-fermare-vannacci-parla-il-leader-di-sud-chiama-nord--409967\" target=\"_blank\" rel=\"noopener noreferrer\">Fonte: intervista al Foglio, 9 ottobre 2026</a>. Verifica: 11 ottobre 2026.</p>"
today = '<main id="oggi" class="page">'+intro+card(pole)+card(intents)+'<section class="card" id="rilevazioni-recenti">'+recent+'</section>'+movement+'</main>'

def chart(keys,labels,colors,low,high):
    width,height=640,280
    start=date.fromisoformat(series[0]['date']); end=date.fromisoformat(as_of)
    def x(s): return 48+550*(date.fromisoformat(s['date'])-start).days/max(1,(end-start).days)
    def y(v): return 225-185*(v-low)/(high-low)
    svg=f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Medie ponderate, punti reali dal {dt(series[0]["date"])} al {dt(as_of)}" style="width:100%;background:#fff;color:#233044">'
    for v in range(low,high+1,1 if high-low<=10 else 5):
        svg+=f'<line x1="48" x2="600" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#d5dbe3"/><text x="6" y="{y(v)+4:.1f}" fill="#233044" font-size="14">{v}%</text>'
    for key,label,color in zip(keys,labels,colors):
        values=[s[key] if key in ['left','right'] else s['parties'][key] for s in series]
        points=' '.join(f'{x(s):.1f},{y(v):.1f}' for s,v in zip(series,values))
        svg+=f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="4.5" vector-effect="non-scaling-stroke" stroke-linecap="round" stroke-linejoin="round"/>'
        for s,v in zip(series,values):
            svg+=f'<circle cx="{x(s):.1f}" cy="{y(v):.1f}" r="4.5" fill="{color}"><title>{dt(s["date"])} · {label}: {fmt(v)}%</title></circle>'
    svg+=f'<text x="48" y="258" fill="#233044" font-size="14">{short_dt(start.isoformat())}</text><text x="515" y="258" fill="#233044" font-size="14">{short_dt(end.isoformat())}</text></svg>'
    return svg+'<p>'+ ' · '.join(f'{label}: {fmt(current[key] if key in ["left","right"] else means[key])}%' for key,label in zip(keys,labels))+'</p>'
trend = '<main id="trend" class="page">'+card(f'<div class="kicker">Snapshot v1 • {dt(as_of)}</div><h1>Trend</h1><p class="sub">Un punto per ogni data con nuovi dati disponibili; una sola rilevazione per istituto nei 42 giorni precedenti. Le linee collegano snapshot, non stime giornaliere.</p>')
trend += card('<h2>I due poli</h2>'+chart(['left','right'],['Centrosinistra','Centrodestra'],['#81b9f0','#f0aa86'],40,55))
trend += card('<h2>Primi tre partiti</h2>'+chart(['fdi','pd','m5s'],['FdI','PD','M5S'],['#8eafe3','#ee92b2','#e4c865'],10,30))
def separate_charts(keys,labels,colors,low,high):
    return '<p class="tiny">Un grafico per partito, tutti con la stessa scala: '+str(low)+'–'+str(high)+'%. Le percentuali non sono spostate per separare le linee.</p><div class="party-trend-grid">'+''.join('<div class="party-trend-panel"><h3>'+label+'</h3>'+chart([key],[label],[color],low,high)+'</div>' for key,label,color in zip(keys,labels,colors))+'</div>'
trend += card('<h2>FN, FI, AVS e Lega</h2>'+separate_charts(['fn','fi','avs','lega'],['Futuro Nazionale','Forza Italia','AVS','Lega'],['#c4a0ed','#81b9f0','#9bcfa4','#eead87'],4,9))
trend += card('<h2>Altri partiti rilevati</h2>'+separate_charts(['azione','iv','europa','nm'],['Azione','Italia Viva','+Europa','Noi Moderati'],['#c4a0ed','#81b9f0','#9bcfa4','#eead87'],0,5))
trend += card('<h2>Snapshot verificabili</h2><div style="overflow-x:auto"><table><thead><tr><th>Data</th><th>Istituti</th><th>CSX</th><th>CDX</th></tr></thead><tbody>'+''.join(f'<tr><td>{dt(s["date"])}</td><td>{len(s["selected_polls"])}</td><td>{fmt(s["left"])}%</td><td>{fmt(s["right"])}%</td></tr>' for s in series)+'</tbody></table></div><p class="tiny">Storico precedente: i grafici della versione del 15 settembre sono conservati nel repository, ma non prolungati perché mancano nel feed i dati di origine per ricostruirli. Nessun punto fittizio è aggiunto. Ogni punto pubblicato supera la soglia di almeno tre istituti e nessuno oltre il 60% per ogni partito.</p>')+'</main>'

h=(ROOT/'index.html').read_text()
h=h.replace('FdI · Lega · Futuro Nazionale · Forza Italia · Noi Moderati</span>', 'FdI · Lega · Futuro Nazionale · Forza Italia · Noi Moderati · Sud chiama Nord (accordo nazionale annunciato; dato separato non disponibile)</span>')
for key,value in [('oggi',today),('trend',trend)]:
    h,n=re.subn(r'<main id="'+key+r'".*?</main>',lambda m:value,h,flags=re.S); assert n==1
# Generate every archive entry, radio and page from the same feed as the averages.
ordered=sorted(polls,key=lambda p:(p['published'],p['id']),reverse=True)
archive='<main id="sondaggi" class="page">'+card(
    '<div class="kicker">Archivio dati</div><h1>Sondaggi</h1>'
    f'<p class="sub">{len(polls)} schede ordinate per pubblicazione. Ultimo dato incluso nella media: {dt(as_of)}.</p>'
    '<label class="poll-link" for="tab-oggi"><div><b>Media e rilevazioni recenti</b><span>Valori, copertura e fonti</span></div><strong>›</strong></label>')
archive+='<section class="card"><div class="poll-list">'
pages=[]
for p in ordered:
    pid='poll-'+p['id']
    archive+=f'<label class="poll-link" for="tab-{pid}"><div><b>{NAMES[p["institute"]]}</b><span>{dt(p["published"])} · {escape(status(p))}</span></div><strong>›</strong></label>'
    heading='<label class="back-link" for="tab-sondaggi">‹ Tutti i sondaggi</label><div class="kicker">Sondaggio singolo</div>'
    heading+=f'<h1>{NAMES[p["institute"]]}</h1><div class="sub"><time datetime="{p["published"]}">{dt(p["published"])}</time></div><div class="visual-note">{escape(status(p))}</div>'
    rows=[]
    for k,v in sorted(p['values'].items(),key=lambda x:-x[1]):
        rows.append(f'<div class="single-row party-{k}"><div class="single-head"><span class="single-name"><i class="party-dot"></i>{PARTIES[k]}</span><b>{str(v).replace(".",",")}%</b></div><div class="single-line"><div class="single-fill" style="width:{v/35*100:.1f}%"></div><span class="single-dot" style="left:{v/35*100:.1f}%"></span></div></div>')
    chart_html='<h2>Intenzioni di voto</h2><div class="single-poll-chart">'+''.join(rows)+'</div><div class="sourcebox">Valori del singolo sondaggio: non è una media VOTO27.</div>'
    pages.append(f'<main id="{pid}" class="page">'+card(heading)+card(chart_html)+card(metadata(p))+'</main>')
archive+='</div></section></main>'
h,n=re.subn(r'<main id="sondaggi".*?</main>',lambda m:archive,h,flags=re.S);assert n==1
h=re.sub(r'<main id="poll-[^"]+".*?</main>\s*','',h,flags=re.S)
h=h.replace('<main id="seggi"', '\n'.join(pages)+'\n<main id="seggi"')
h=re.sub(r'<input[^>]*id="tab-poll-[^"]+"[^>]*>\s*','',h)
radios='\n'.join(f'<input class="tab-radio" type="radio" name="tabs" id="tab-poll-{p["id"]}">' for p in ordered)
h=h.replace('<div class="app">',radios+'\n<div class="app">')
h=re.sub(r'#tab-poll-[^\s{]+:checked ~ \.app #poll-[^\s{]+\{display:block\}\s*','',h)
h=re.sub(r'#tab-poll-[^\s{]+:checked ~ nav[^{}]*\{[^{}]*\}\s*','',h)
h=re.sub(r'<style id="generated-poll-navigation">.*?</style>\s*','',h,flags=re.S)
navigation='\n'.join(f'#tab-poll-{p["id"]}:checked ~ .app #poll-{p["id"]}{{display:block}}\n#tab-poll-{p["id"]}:checked ~ nav label[for="tab-sondaggi"]{{color:var(--text);background:var(--soft)}}' for p in ordered)
h=h.replace('</head>','<style id="generated-poll-navigation">\n'+navigation+'\n</style>\n</head>')
h=h.replace('Per gli snapshot storici viene usata una finestra massima di 42 giorni.','Per medie correnti e snapshot storici viene usata una finestra massima di 42 giorni con una sola rilevazione per istituto, indipendentemente dalla frequenza di pubblicazione. Le date di pubblicazione sono la base temporale uniforme di questo feed; le date delle interviste restano separate.')
h=re.sub(r'(<h3>3\. Media per partito</h3>\s*)<p>.*?</p>',r'\1<p>Per ciascun partito calcoliamo separatamente la media ponderata delle rilevazioni in cui quel partito è effettivamente presente. Non assegniamo valori inventati alle liste non testate. Metodo o campione mancanti non escludono da soli valori nazionali comparabili e verificati, purché istituto e data siano identificabili. La copertura è indicata per partito.</p>',h,flags=re.S)
h=re.sub(r'<section class="card method-card">\s*<h3>6\..*?</section>',card('<h3>6. Limiti del modello</h3><p>Le correzioni per differenze sistematiche tra istituti non sono applicate. Lo storico visualizzato copre soltanto snapshot ricostruibili dal feed disponibile: eventuali lacune restano esplicite.</p>'),h,flags=re.S)
h=re.sub(r'<section class="card method-card">\s*<h3>8\..*?</section>',card('<h3>8. Controllo qualità</h3><p>Ogni punto del grafico richiede almeno tre istituti e nessun istituto oltre il 60% del peso per ciascun partito. Le rilevazioni di uno stesso istituto, incluso Only Numbers / Realpolitik, non si duplicano.</p>'),h,flags=re.S)
h=re.sub(r'<section class="card method-card"><h3>9\..*?</section>',card('<h3>9. Stato del metodo</h3><p>Metodo v1: medie per partito, ponderazione temporale e copertura dichiarata. I dati storici anteriori alla serie ricostruibile non sono estesi artificialmente.</p>'),h,flags=re.S)
h,n=re.subn(r'PASS</b> \(\d+ sondaggi(?: nel feed)?\)',f'PASS</b> ({len(polls)} sondaggi nel feed)',h);assert n==1
config=json.loads((ROOT/'data/config.json').read_text())
config.update(data_last_update=as_of,sources_verified_on=data['verified_on'],cards_updated_on=data['verified_on'])
config['aggregation'].update(current_lookback_days=42,current_one_poll_per_institute=True,date_basis='publication')
(ROOT/'data/config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
h=re.sub(r'const CONFIG = .*?;',lambda m:'const CONFIG = '+json.dumps(config,ensure_ascii=False)+';',h)
h=h.replace('.party:hover{background:#fafbfd}', '')
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
party_css = '#oggi .party summary,#oggi .party summary .pname,#oggi .party summary b{color:#f4f6f8 !important}#oggi .party[open]{background:#1b2631}#oggi .party .party-detail{color:#c5ccd5 !important}#oggi .party summary:focus-visible{outline:2px solid #9cc4e5;outline-offset:2px;border-radius:12px}#oggi .party summary .pname::after{content:"⌄";font-size:14px;color:#a9c9e7;margin-left:4px}#oggi .party[open] summary .pname::after{content:"⌃"}@media(hover:hover) and (pointer:fine){#oggi .party:hover{background:#1b2631}}'
separate_css = '.party-trend-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.party-trend-panel{min-width:0;padding-top:10px;border-top:1px solid #3b4652}.party-trend-panel h3{margin:8px 0;font-size:16px}.party-trend-panel p{font-size:13px}@media(max-width:640px){.party-trend-grid{grid-template-columns:1fr;gap:14px}}'
style=style.replace('</style>',palette_css+party_css+separate_css+'</style>')
if 'id="verified-data-style"' in h:
    h=re.sub(r'<style id="verified-data-style">.*?</style>',lambda m:style.strip(),h,flags=re.S)
else:
    h=h.replace('</head>',style+'</head>')
ids=re.findall(r'\bid="([^"]+)"',h); assert len(ids)==len(set(ids))
assert 'ricalcolo della serie e dei grafici è in corso' not in h
(ROOT/'index.html').write_text(h)
# Refresh offline assets whenever the generated page changes, including same-day edits.
sw=(ROOT/'sw.js').read_text()
sw=re.sub(r"const CACHE = '[^']+';", "const CACHE = 'voto27-v1-"+hashlib.sha256(h.encode()).hexdigest()[:12]+"';", sw)
(ROOT/'sw.js').write_text(sw)
print(json.dumps({'as_of':as_of,'means':means,'left':left,'right':right,'polls':len(polls),'institutes':len(current['selected_polls']),'snapshots':len(series)},ensure_ascii=False,indent=2))

