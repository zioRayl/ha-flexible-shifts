# Flexible Shifts

Dopo l'avvio aprire l'interfaccia web e creare il primo utente dal menu a rotellina.

## Configurazione iniziale

Per ogni utente impostare:

- part-time o full-time;
- ore previste su base settimanale o mensile;
- metodo di conversione mensile, se la base è settimanale;
- intervallo accettabile degli straordinari.

La vista iniziale è settimanale, da lunedì a domenica. Il selettore utenti consente di visualizzare più persone contemporaneamente.

## Turni e pause

Ogni giornata può contenere un solo turno con:

- Inizio turno;
- Fine turno;
- pausa facoltativa con inizio e fine.

La durata della pausa viene sottratta automaticamente dal totale.

## Preset orari

Dal menu **Preset orari** è possibile creare preset separati per ogni utente. Ogni preset include nome, inizio turno, fine turno e pausa facoltativa. Nel modulo di inserimento turno basta selezionare il preset per compilare gli orari.

## Persistenza

Il database è salvato in `/data/flexible_shifts.db` ed è incluso nei backup di Home Assistant.

## Importazione

Dal menu **Importa / Esporta** è possibile scaricare un modello CSV, importare dati storici ed esportare un anno completo. I vecchi CSV con due coppie Start/Stop restano supportati: vengono convertiti in un unico turno con pausa intermedia.


## Accesso utenti

La voce **Turni** è accessibile a tutti gli utenti autenticati di Home Assistant. La gestione dell’add-on (installazione, aggiornamento, avvio e configurazione) rimane invece riservata agli amministratori di Home Assistant.
