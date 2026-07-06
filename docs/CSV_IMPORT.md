# Importazione CSV

Il formato consigliato è:

```csv
data;data_fine;tipo;inizio_turno;fine_turno;inizio_pausa;fine_pausa;ore_accreditate;note
2026-01-05;;work;08:30;14:30;;;;Turno mattina
2026-01-06;;work;08:00;19:30;11:00;15:00;;Turno con pausa
2026-01-12;;ferie;;;;;;;Singolo giorno di ferie
2026-02-02;2026-02-08;ferie;;;;;;;Intervallo di ferie
```

## Ferie

- `data` indica il primo giorno.
- `data_fine` è facoltativa; se vuota, la ferie riguarda un solo giorno.
- `ore_accreditate` è facoltativa; se vuota viene calcolata dal contratto.
- `ferie_settimana` continua a creare una settimana completa per compatibilità.
- Una vecchia riga `ferie` senza `data_fine`, ma con credito simile alle ore settimanali, viene interpretata come settimana completa.

Sono accettate date ISO e italiane e separatori `;`, `,` o tabulazione.
