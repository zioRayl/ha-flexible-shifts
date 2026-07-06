# Analisi del foglio di origine

Il PDF fornito contiene sette pagine di calendario e una pagina di report.

## Calendario

- Ogni settimana è organizzata da lunedì a domenica.
- Ogni giorno dispone di due righe Start/Stop, quindi può rappresentare un turno spezzato.
- Il totale è calcolato per singola settimana.
- Gli orari usano ore decimali: `6,5` equivale a `06:30`, `19,5` a `19:30`.
- Una settimana di ferie è rappresentata con un valore fittizio `0-30,5` sul lunedì e gli altri giorni vuoti. Nella nuova applicazione questa convenzione è sostituita da un record ferie esplicito.

## Report

La pagina finale contiene le colonne:

- Mese;
- Ore Totali;
- Straordinari;
- Standard;
- GWE Lavorati;
- Su;
- Ferie;
- percentuale.

Dai valori risulta che:

- `Standard = 30,5 × 4 = 122`;
- `Straordinari = Ore Totali - Standard`, quando positivo;
- `Su` rappresenta il numero di sabati e domeniche nel mese;
- la percentuale è `GWE Lavorati / Su`.

Il titolo del riepilogo mostra `Anno 2025`, mentre le pagine calendario riportano date del 2026. La nuova applicazione usa un selettore anno e non dipende da un titolo scritto manualmente.
