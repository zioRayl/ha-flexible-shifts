# Importazione CSV

L'importazione è associata all'utente selezionato nell'interfaccia.

## Formato consigliato

| Colonna | Obbligatoria | Descrizione |
|---|---:|---|
| `data` | sì | Data ISO `2026-01-05` oppure italiana `05/01/2026` |
| `tipo` | no | `work` per un turno, `ferie` per una settimana di ferie |
| `inizio_turno` | per i turni | Ora di inizio |
| `fine_turno` | per i turni | Ora di fine |
| `inizio_pausa` | no | Inizio della pausa da sottrarre |
| `fine_pausa` | no | Fine della pausa da sottrarre |
| `ore_accreditate` | no | Ore ferie, altrimenti calcolate dal contratto |
| `note` | no | Testo libero |

Sono accettati orari come `13:30`, `13.30`, `13,5` o `13.5`.

Esempio:

```csv
data;tipo;inizio_turno;fine_turno;inizio_pausa;fine_pausa;ore_accreditate;note
2026-01-05;work;08:30;14:30;;;;Turno mattina
2026-01-06;work;08:00;19:30;11:00;15:00;;Turno con pausa
2026-01-12;ferie;;;;;30,5;Settimana ferie
```

## Compatibilità con il vecchio foglio Google

Restano accettate le colonne:

```text
start_1, end_1, start_2, end_2, pause_start, pause_end
```

Quando sono presenti due coppie Start/Stop e non è presente una pausa esplicita, l'importatore applica automaticamente questa conversione:

- `start_1` = Inizio turno;
- `end_2` = Fine turno;
- `end_1` = Inizio pausa;
- `start_2` = Fine pausa.

Esempio vecchio formato:

```csv
data;tipo;start_1;end_1;start_2;end_2;pause_start;pause_end;ore_accreditate;note
2026-01-06;work;08:00;11:00;15:00;19:30;;;;Turno con pausa
```

Viene importato come turno `08:00-19:30` con pausa `11:00-15:00`.

## Aggiornamento dei dati

Esiste un solo turno per utente e data. Importando nuovamente la stessa data, il turno esistente viene aggiornato invece di essere duplicato.
