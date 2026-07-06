# Flexible Shifts 0.3.0

## Report annuale

La tabella è ora ordinata così:

`Mese · Ore totali · Straordinari · Standard · GWE lavorati · Su · % · Settimane Ferie`

Il campo **Saldo** è stato rimosso sia dalla tabella sia dal riepilogo laterale. La percentuale weekend è stata spostata subito dopo **Su** e la colonna **Ferie** è stata rinominata **Settimane Ferie**.

## Ferie giornaliere e per intervallo

Le ferie non sono più vincolate alla settimana intera. È possibile inserire:

- un singolo giorno;
- più giorni consecutivi;
- una settimana completa, selezionando il relativo intervallo.

Il credito orario viene calcolato automaticamente in proporzione al contratto:

- full-time: vengono conteggiati i giorni da lunedì a venerdì;
- part-time: vengono conteggiati i giorni da lunedì a domenica.

Nel report **Settimane Ferie** mostra l'equivalente frazionario. Per esempio, un giorno full-time corrisponde a `0,20` settimane; un giorno part-time corrisponde a circa `0,14` settimane.

Le ferie già presenti nel database restano valide e vengono conteggiate senza migrazioni distruttive.


## Accesso per tutti gli utenti Home Assistant

La voce **Turni** e l'interfaccia Ingress non sono più limitate agli amministratori. Il parametro `panel_admin` è impostato a `false`, quindi ogni utente autenticato di Home Assistant può aprire e utilizzare l'applicazione.

## CSV

L'importazione e l'esportazione supportano la nuova colonna facoltativa `data_fine`:

```csv
data;data_fine;tipo;inizio_turno;fine_turno;inizio_pausa;fine_pausa;ore_accreditate;note
2026-01-12;;ferie;;;;;;;Giorno singolo
2026-02-02;2026-02-08;ferie;;;;;;;Intervallo ferie
```

Le vecchie righe settimanali con credito pari alle ore settimanali vengono riconosciute automaticamente.

## Verifiche

- 16 test automatici superati;
- sintassi Python e JavaScript verificata;
- nessuna modifica distruttiva allo schema SQLite.
