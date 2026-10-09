# VOTO27 1.0

Versione stabile per https://voto27.netlify.app/

La 1.0 congela metodo v1, struttura mobile-first, storico annuale, scenario a due poli, gestione separata di affluenza/non risposta e predisposizione blackout.

## Aggiornamenti dei sondaggi

Il sito è statico: le schede dei sondaggi, le medie, i grafici e le date visibili sono attualmente incorporati in `index.html`. `data/config.json` contiene impostazioni e una data di aggiornamento, ma la pagina non lo carica a runtime. `data/new_poll_template.json` descrive i campi da raccogliere per ogni nuova rilevazione; non pubblica automaticamente il sondaggio.

Il controllo programmato di ChatGPT cerca nuove rilevazioni nazionali da fonti primarie, verifica istituto, data di pubblicazione, periodo, campione/metodo e percentuali, e confronta ogni rilevazione con le schede già presenti nel repository. Conserva le etichette originali di affluenza, indecisi e non risposta; segnala i dati mancanti e le rilevazioni non comparabili. Non inventa percentuali, non trasforma la non risposta in astensione e non modifica il metodo v1 (peso exp(-giorni/21), finestra storica 42 giorni, un sondaggio per istituto negli snapshot storici, Azione e «Altri» non assegnati).

Per pubblicare un nuovo sondaggio aggiornare `data/polls.json` e rigenerare la pagina con `python scripts/update_site.py`: selettori, schede, archivio, fonti, medie, poli, grafici e metadati derivano dal feed. `data/new_poll_template.json` usa lo stesso schema: `values` contiene soltanto le chiavi dei partiti verificate, senza valori nulli o inventati. Lo script aggiorna `data/config.json` e il CONFIG incorporato quando cambia la data dell'ultimo dato incluso. Non alterare date o medie soltanto perché è trascorso un giorno. Se manca una tabella completa si aggiornano i soli indicatori calcolabili sui valori verificati, dichiarando la copertura; gli indicatori incompatibili restano fuori media. Un impedimento su una fonte non blocca gli altri valori affidabili: escludere soltanto quanto non verificabile e segnalare la lacuna.

Il push su `main` attiva la distribuzione Netlify. Prima di pubblicare, controllare che l'HTML sia valido, gli identificatori delle schede siano unici, i collegamenti alle fonti funzionino e le cifre visibili siano coerenti con le rilevazioni utilizzate. Durante un eventuale periodo di blackout elettorale applicabile, non pubblicare nuovi sondaggi.

## Rigenerazione verificabile

`data/polls.json` conserva le rilevazioni e i campi mancanti. Eseguire `python scripts/update_site.py` dalla radice dopo ogni aggiunta o correzione verificata. Lo script genera le sezioni statiche Oggi, Trend e Sondaggi, tutte le schede e la navigazione, `data/derived.json` e le date coerenti in `data/config.json` e nel CONFIG incorporato. Non richiede dipendenze esterne.

Per medie correnti e storiche: finestra inclusiva di 42 giorni, peso exp(-giorni/21), una sola ultima rilevazione comparabile per istituto. Only Numbers e Only Numbers–Realpolitik sono lo stesso istituto. La base temporale uniforme del feed è la prima data di pubblicazione, separata dal periodo delle interviste; una ripubblicazione non crea un nuovo sondaggio. Per ciascun partito vengono usati solo i valori presenti nell’ultima scheda selezionata, senza recuperare dati mancanti da schede precedenti. Una scheda parziale non blocca gli indicatori calcolabili; campione/metodo mancanti sono dichiarati, ma non bastano a escludere valori comparabili con istituto, data e fonte verificati.

I poli sono somme delle medie per partito e hanno copertura eterogenea, esplicitata nella pagina. Il residuo 100 meno i poli non è una rilevazione di Altri. Gli snapshot del grafico richiedono almeno tre istituti e nessuno oltre il 60% del peso per ciascun partito. Punti reali soltanto alle date dei dati; nessuna estensione giornaliera o mensile inventata.

Lo storico precedente, non ricostruibile dal feed attuale, è conservato in `data/legacy-trend.html` come archivio della versione del 15 settembre, non prolungato nei grafici correnti. Le schede originarie senza link conservato restano riconoscibili come dati ereditati dall’archivio VOTO27 e non vengono presentate come nuovamente verificate.

La data della media (`data_last_update`) è l’ultima pubblicazione comparabile inclusa; `sources_verified_on` e `cards_updated_on` indicano il controllo delle fonti e la rigenerazione. Le schede escluse non avanzano la data delle medie. Il conteggio del feed include anche schede storiche ed escluse: non rappresenta il numero degli istituti nella media. `metadata_origin` identifica i metadati ereditati; `archive_metadata` conserva il testo precedente senza attribuirgli una nuova verifica. `extra_values` conserva aggregazioni e liste fuori dalle 11 medie.

Eseguire `python scripts/check_site.py` dopo la rigenerazione per controllare date, navigazione, selezione degli istituti, valori visibili e grafici, oltre alla riproducibilità della generazione. La cache offline viene aggiornata quando cambia l’HTML generato.
