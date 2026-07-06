# Release 0.1.0 - Prima versione di prova

## Implementato

- Repository installabile in Home Assistant OS come app/add-on locale o da GitHub.
- Interfaccia Ingress accessibile dalla barra laterale.
- Vista predefinita settimanale lunedì-domenica.
- Viste giorno e mese.
- Navigazione avanti/indietro tra periodi.
- Selettore multiplo utenti.
- Gestione utenti con:
  - part-time/full-time;
  - obiettivo settimanale/mensile;
  - conversione mensile x4 o 52/12;
  - soglia straordinari minima/massima;
  - attivazione/disattivazione.
- Turni con massimo due intervalli Start/Stop.
- Pausa esplicita sottratta dal totale.
- Ferie settimanali lunedì-venerdì per full-time e lunedì-domenica per part-time.
- Report annuale in tempo reale con logica compatibile con il foglio fornito.
- Conteggio weekend per part-time.
- Importazione CSV, esportazione CSV e backup SQLite.
- Pubblicazione sensori Home Assistant.
- Test automatici Python e controllo sintattico JavaScript.

## Assunzioni della versione iniziale

- Per un utente con 30,5 ore settimanali, lo standard mensile predefinito è 122 ore (`30,5 × 4`), come nel report di origine.
- Le ferie sono conteggiate nel totale ore tramite accredito settimanale, ma non nei weekend lavorati.
- Il totale annuale dello standard considera i mesi trascorsi dell'anno corrente.
- L'accesso dalla barra laterale è riservato agli amministratori Home Assistant nella versione 0.1.0.

## Verifiche eseguite

- Compilazione di tutti i moduli Python.
- Validazione sintattica del JavaScript con Node.js.
- Validazione YAML dei file di repository, configurazione, traduzione e workflow.
- 8 test automatici superati su calcoli, API, ferie e importazione CSV.
