# Changelog

## 0.4.0

- Aggiunto un colore personalizzabile per ogni utente.
- Applicato il colore a turni, ferie, vista mensile, vista giornaliera, riepiloghi ed elenchi utenti.
- Aggiunta migrazione automatica del database con assegnazione di colori distinti agli utenti esistenti.
- Ottimizzato il layout responsive per desktop, tablet e smartphone.
- La vista settimanale passa da 7 a 4, 2 o 1 colonna in base allo spazio disponibile.
- La vista mensile diventa un elenco cronologico leggibile sui dispositivi più piccoli.

## 0.3.0

- Riordinato il report annuale: Mese, Ore totali, Straordinari, Standard, GWE lavorati, Su, %, Settimane Ferie.
- Rimosso il Saldo dalla tabella e dal riepilogo del report.
- Le ferie possono essere inserite per un singolo giorno o per un intervallo libero.
- Il credito ferie automatico viene calcolato in proporzione ai giorni selezionati.
- Per i full-time si conteggiano lunedì-venerdì; per i part-time lunedì-domenica.
- Le Settimane Ferie sono espresse come equivalente frazionario.
- Migliorate importazione ed esportazione CSV con la colonna `data_fine`.
- Mantenuta la compatibilità con le ferie settimanali già salvate e con il payload 0.2.x.
- Resa la voce Turni accessibile a tutti gli utenti autenticati di Home Assistant (`panel_admin: false`).

## 0.2.0

- Sostituiti gli intervalli multipli con un solo Inizio turno e una sola Fine turno.
- Mantenuta una pausa opzionale da sottrarre dal conteggio.
- Aggiunti preset orari personalizzati per singolo utente.
- Aggiunta gestione completa dei preset: creazione, modifica, eliminazione e applicazione al turno.
- Aggiunta migrazione automatica dei vecchi turni con due intervalli in un turno unico con pausa.
- Aggiornato il formato CSV; i vecchi CSV con doppio Start/Stop restano compatibili.

## 0.1.1

- Corretto l'avvio con FastAPI/Python 3.14: gli endpoint DELETE restituiscono una risposta HTTP 204 esplicita senza corpo.
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
