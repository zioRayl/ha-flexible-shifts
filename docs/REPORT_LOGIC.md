# Logica dei report

## Colonne del report mensile

1. **Mese**
2. **Ore totali**: ore lavorate più ore ferie accreditate.
3. **Straordinari**: `max(0, ore totali - standard)`.
4. **Standard**: obiettivo mensile dell'utente.
5. **GWE lavorati**: sabati e domeniche con un turno, per utenti part-time.
6. **Su**: numero totale di sabati e domeniche presenti nel mese.
7. **%**: `GWE lavorati / Su × 100`.
8. **Settimane Ferie**: equivalente in settimane dei giorni di ferie del mese.

Il **Saldo** non viene più visualizzato. Rimane disponibile internamente nell'API per compatibilità con versioni precedenti.

## Calcolo delle ferie

Le ferie possono coprire un singolo giorno o un intervallo di date.

- Full-time: sono validi lunedì-venerdì; una settimana equivale a 5 giorni.
- Part-time: sono validi lunedì-domenica; una settimana equivale a 7 giorni.

Il credito automatico è:

`ore settimanali × giorni di ferie validi / giorni contrattuali per settimana`

Esempi:

- full-time 40 h, un giorno: `40 / 5 = 8 h`, pari a `0,20` settimane;
- part-time 30,5 h, un giorno: `30,5 / 7 = 4,357... h`, pari a `0,142857...` settimane;
- settimana completa: `1,00` settimana.

Se un intervallo attraversa due mesi, ore e settimane equivalenti vengono ripartite in proporzione ai giorni validi ricadenti in ciascun mese.
