# Logica della reportistica

## Colonne mensili

- **Ore totali**: ore dei turni più ore accreditate per ferie.
- **Straordinari**: `max(0, ore totali - standard)`.
- **Standard**: obiettivo mensile dell'utente oppure conversione dell'obiettivo settimanale.
- **Saldo**: `ore totali - standard`, quindi può essere negativo.
- **GWE lavorati**: per i soli part-time, numero di date distinte di sabato o domenica con almeno un turno lavorato.
- **Su**: per i soli part-time, numero totale di sabati e domeniche presenti nel mese.
- **Ferie**: numero di settimane di ferie che iniziano nel mese.
- **%**: `GWE lavorati / Su × 100`.

## Soglia straordinari

Ogni utente ha una soglia minima e massima. Con la configurazione 0-12 ore:

- da 0 a 12 ore: stato accettabile;
- oltre 12 ore: stato eccessivo.

Il colore del valore nella tabella annuale riflette questa soglia.

## Totali annuali

Per l'anno corrente il riepilogo considera gennaio fino al mese corrente. Per un anno passato considera tutti i dodici mesi. Le righe future restano visibili ma attenuate.

## Ferie

Una settimana di ferie accredita:

- le ore settimanali, se l'utente è configurato su base settimanale;
- un quarto delle ore mensili, se è configurato su base mensile.

La ferie non incrementano il numero di weekend lavorati.
