# Changelog


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
