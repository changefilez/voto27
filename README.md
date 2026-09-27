# VOTO27 1.0

Versione stabile per https://voto27.netlify.app/

La 1.0 congela metodo v1, struttura mobile-first, storico annuale, scenario a due poli, gestione separata di affluenza/non risposta e predisposizione blackout.

## Aggiornamenti dei sondaggi

Il sito è statico: le schede dei sondaggi, le medie, i grafici e le date visibili sono attualmente incorporati in `index.html`. `data/config.json` contiene impostazioni e una data di aggiornamento, ma la pagina non lo carica a runtime. `data/new_poll_template.json` descrive i campi da raccogliere per ogni nuova rilevazione; non pubblica automaticamente il sondaggio.

Il controllo programmato di ChatGPT cerca nuove rilevazioni nazionali da fonti primarie, verifica istituto, data di pubblicazione, periodo, campione/metodo e percentuali, e confronta ogni rilevazione con le schede già presenti nel repository. Conserva le etichette originali di affluenza, indecisi e non risposta; segnala i dati mancanti e le rilevazioni non comparabili. Non inventa percentuali, non trasforma la non risposta in astensione e non modifica il metodo v1 (peso exp(-giorni/21), finestra storica 42 giorni, un sondaggio per istituto negli snapshot storici, Azione e «Altri» non assegnati).

Per pubblicare un nuovo sondaggio occorre aggiornare `index.html` in modo coerente: selettore/scheda, elenco dei sondaggi, fonti e, solo per rilevazioni comparabili con valori sufficienti, medie correnti, poli e grafici derivati. Aggiornare `data/config.json` insieme alla pagina quando cambia la data dell'ultimo aggiornamento *dei dati effettivamente mostrati*. Non alterare date o medie soltanto perché è trascorso un giorno. Se manca una tabella completa si può mostrare una scheda «fuori media» senza cambiare le medie. Se non è possibile verificare la fonte, ricostruire la media o controllare la coerenza della pagina, lasciare il sito intatto e segnalare il blocco.

Il push su `main` attiva la distribuzione Netlify. Prima di pubblicare, controllare che l'HTML sia valido, gli identificatori delle schede siano unici, i collegamenti alle fonti funzionino e le cifre visibili siano coerenti con le rilevazioni utilizzate. Durante un eventuale periodo di blackout elettorale applicabile, non pubblicare nuovi sondaggi.
