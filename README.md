# HA Flexible Shifts

Repository Home Assistant per gestire turni completamente variabili, pause, ferie settimanali e report annuali.

La prima versione nasce dalla struttura del foglio `Orari 2026`: calendario con due coppie Start/Stop per giorno, totale settimanale e report annuale con ore totali, straordinari, standard, giorni weekend lavorati, weekend disponibili, settimane di ferie e percentuale.

## Funzioni incluse

- Più utenti nella stessa installazione.
- Selettore multiplo utenti nella parte alta.
- Vista predefinita settimanale, oltre a giorno e mese.
- Navigazione tra settimane, mesi e anni precedenti.
- Turni non standard con uno o più intervalli di lavoro.
- Pausa opzionale con ora di inizio e fine, sottratta dal conteggio.
- Ferie gestite come settimana:
  - full-time: lunedì-venerdì;
  - part-time: lunedì-domenica.
- Obiettivo contrattuale settimanale oppure mensile per ogni utente.
- Soglia individuale degli straordinari, per esempio 0-12 ore accettabili.
- Report annuale aggiornato in tempo reale.
- Per i part-time: giorni di sabato/domenica lavorati, giorni weekend disponibili e percentuale.
- Importazione ed esportazione CSV.
- Backup del database SQLite.
- Sensori pubblicati automaticamente in Home Assistant.
- Stampa del report annuale o salvataggio in PDF dal browser.

## Installazione in Home Assistant

1. Caricare questa cartella in un repository GitHub pubblico.
2. In Home Assistant aprire **Impostazioni > Componenti aggiuntivi > Add-on Store**.
3. Aprire il menu in alto a destra, scegliere **Repository** e aggiungere l'URL GitHub.
4. Installare **Flexible Shifts**.
5. Avviare l'add-on e abilitare **Mostra nella barra laterale**.

Esempio di pubblicazione:

```bash
git init
git add .
git commit -m "Release 0.1.1"
git branch -M main
git remote add origin https://github.com/NOME-UTENTE/ha-flexible-shifts.git
git push -u origin main
```

## Primo avvio

Dal menu a rotellina:

1. Aprire **Gestione utenti**.
2. Creare almeno un utente.
3. Indicare full-time/part-time, base settimanale/mensile, ore previste e soglia straordinari.
4. Inserire i turni dal pulsante **+ Turno**.
5. Inserire una settimana di ferie dal pulsante **+ Ferie**.
6. Aprire **Reportistica annuale** per il riepilogo.

## Regola dello standard mensile

Per un contratto espresso su base settimanale sono disponibili due metodi:

- `ore settimanali × 4`: impostazione predefinita, compatibile con il foglio fornito. Per 30,5 ore produce 122 ore mensili.
- `ore settimanali × 52 / 12`: media mensile annualizzata.

Per un contratto espresso su base mensile, lo standard è il valore mensile inserito.

## Sensori Home Assistant

Per ogni utente attivo vengono creati o aggiornati:

```text
sensor.turni_<utente>_ore_mese
sensor.turni_<utente>_straordinari_mese
sensor.turni_<utente>_weekend_lavorati_mese
sensor.turni_<utente>_ore_anno
sensor.turni_<utente>_prossimo_turno
binary_sensor.turni_<utente>_al_lavoro
```

La sincronizzazione usa il token Supervisor disponibile agli add-on e può essere disabilitata dalle opzioni.

## Dati e backup

Il database è memorizzato in:

```text
/data/flexible_shifts.db
```

Il pulsante **Scarica backup** crea e scarica una copia SQLite. I dati restano nella cartella `/data` anche durante l'aggiornamento dell'add-on.

## Importazione storica

Consultare [docs/CSV_IMPORT.md](docs/CSV_IMPORT.md). È incluso anche [samples/import_template.csv](samples/import_template.csv).

## Limiti della versione 0.1.1

- Fino a due intervalli di lavoro e un intervallo di pausa esplicita per giorno nell'interfaccia.
- Il PDF del report viene prodotto tramite la funzione Stampa/Salva PDF del browser.
- Non sono ancora presenti maggiorazioni economiche, banca ore, festività nazionali automatiche o ruoli di accesso separati.
- L'importatore non legge direttamente PDF o fogli Google: il formato di interscambio previsto è CSV.

## Sviluppo locale

```bash
cd flexible_shifts/app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SHIFT_MANAGER_DB=/tmp/flexible_shifts.db
export SHIFT_MANAGER_HA_SYNC=false
python main.py
```

Aprire `http://localhost:8099`.
