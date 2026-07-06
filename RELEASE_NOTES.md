# Release 0.2.0 - Turno singolo e preset orari

## Novità

- Il modulo turno ora mostra solo **Inizio turno** e **Fine turno**.
- Rimane disponibile una pausa facoltativa con inizio e fine, sottratta dal totale.
- Ogni utente può avere preset orari indipendenti.
- I preset si creano dal menu a rotellina oppure direttamente dal modulo turno.
- Selezionando un preset vengono compilati automaticamente inizio, fine e pausa.

## Compatibilità dati

Al primo avvio, i vecchi turni salvati con due intervalli vengono convertiti automaticamente:

- primo Start -> Inizio turno;
- secondo Stop -> Fine turno;
- primo Stop -> Inizio pausa;
- secondo Start -> Fine pausa.

L'importatore continua ad accettare anche i vecchi CSV con `start_1`, `end_1`, `start_2` ed `end_2`, interpretando la seconda coppia come pausa intermedia.

## Aggiornamento

Caricare i file sul repository GitHub, far rilevare l'aggiornamento a Home Assistant e aggiornare l'add-on alla versione 0.2.0. Il database esistente viene mantenuto.
