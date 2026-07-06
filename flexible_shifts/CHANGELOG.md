# Changelog

## 0.2.0

- Sostituiti gli intervalli multipli con un solo Inizio turno e una sola Fine turno.
- Mantenuta una pausa opzionale da sottrarre dal conteggio.
- Aggiunti preset orari personalizzati per singolo utente.
- Aggiunta gestione completa dei preset: creazione, modifica, eliminazione e applicazione al turno.
- Aggiunta migrazione automatica dei vecchi turni con due intervalli in un turno unico con pausa.
- Aggiornato il formato CSV; i vecchi CSV con doppio Start/Stop restano compatibili.


## 0.1.1

- Corretto l'avvio con FastAPI/Python 3.14: gli endpoint DELETE ora restituiscono una risposta HTTP 204 esplicita senza corpo.
- Aggiunti test automatici per eliminazione utenti, turni e ferie.

## 0.1.0

- Prima versione installabile come add-on Home Assistant.
- Utenti multipli e selezione multipla nella vista calendario.
- Viste giorno, settimana e mese con navigazione storica.
- Turni con più intervalli di lavoro e pause esplicite.
- Ferie settimanali con regole full-time e part-time.
- Report annuale in tempo reale.
- Conteggio weekend lavorati e weekend disponibili.
- Soglie individuali per gli straordinari.
- Importazione ed esportazione CSV.
- Backup del database SQLite.
- Pubblicazione sensori in Home Assistant tramite Supervisor API.
