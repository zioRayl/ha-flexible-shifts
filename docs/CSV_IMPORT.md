# Importazione CSV

L'importatore accetta file UTF-8 con separatore `;`, `,` oppure tabulazione. Per gli orari decimali con virgola, per esempio `13,5`, è consigliato il punto e virgola.

## Colonne

| Colonna | Obbligatoria | Descrizione |
|---|---:|---|
| `data` | sì | `AAAA-MM-GG`, `GG/MM/AAAA`, `GG-MM-AAAA` o `GG.MM.AAAA` |
| `tipo` | no | `work`/`lavoro` oppure `ferie`/`vacation` |
| `start_1` | per lavoro | Primo inizio |
| `end_1` | per lavoro | Prima fine |
| `start_2` | no | Secondo inizio per turno spezzato |
| `end_2` | no | Seconda fine |
| `pause_start` | no | Inizio pausa da sottrarre |
| `pause_end` | no | Fine pausa |
| `ore_accreditate` | no | Ore attribuite a una settimana di ferie |
| `note` | no | Testo libero |

Sono riconosciuti anche vari alias italiani e inglesi, come `inizio_1`, `fine_1`, `entrata1`, `uscita1`, `pausa_inizio` e `pausa_fine`.

## Formati orario

Sono accettati:

```text
13:30
13.30
13,5
13.5
```

`13,5` e `13.5` equivalgono alle 13:30.

## Turni spezzati

```csv
data;tipo;start_1;end_1;start_2;end_2;pause_start;pause_end;ore_accreditate;note
2026-01-06;work;08:30;14:30;15:00;19:30;;;;Turno spezzato
```

Il periodo tra 14:30 e 15:00 non viene conteggiato perché i due intervalli sono separati.

## Pausa esplicita

```csv
data;tipo;start_1;end_1;start_2;end_2;pause_start;pause_end;ore_accreditate;note
2026-01-07;work;08:00;17:00;;;12:30;13:00;;Pausa pranzo
```

Il turno vale 8,5 ore.

## Ferie

```csv
data;tipo;start_1;end_1;start_2;end_2;pause_start;pause_end;ore_accreditate;note
2026-01-12;ferie;;;;;;;30,5;Settimana ferie
```

La data viene riportata automaticamente al lunedì della stessa settimana. Se `ore_accreditate` è vuoto, vengono usate le ore settimanali dell'utente oppure un quarto delle ore mensili.

## Aggiornamento di dati esistenti

Una riga di lavoro con lo stesso utente e la stessa data sostituisce il turno già presente. Una settimana di ferie con lo stesso lunedì sostituisce quella esistente.
