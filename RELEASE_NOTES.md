# Flexible Shifts 0.4.0

## Colore personale per utente

In **Gestione utenti** è disponibile un selettore colore. Il colore viene salvato nel profilo e utilizzato per:

- bordo sinistro dei turni nella vista settimanale;
- elementi della vista mensile;
- ferie dell’utente;
- schede della vista giornaliera e riepiloghi;
- indicatori nell’elenco e nel selettore utenti.

Gli utenti esistenti ricevono automaticamente colori distinti alla prima esecuzione della nuova versione. Il database viene migrato senza perdere turni, ferie o preset.

## Interfaccia responsive

L’impaginazione ora dipende dalla larghezza effettivamente disponibile nell’Ingress, senza basarsi sullo user-agent:

- desktop: settimana e mese fino a 7 colonne;
- tablet e finestre intermedie: griglie da 4 o 2 colonne;
- smartphone: una scheda per riga, toolbar e finestre di dialogo adattate;
- vista mensile mobile convertita in elenco cronologico, con giorno della settimana visibile;
- report, gestione utenti, preset e importazione mantengono lo scorrimento solo dove necessario.

## Compatibilità

- aggiornamento dello schema SQLite con la sola colonna `users.color`;
- API utenti compatibile con il nuovo campo `color` in formato esadecimale `#RRGGBB`;
- dati delle versioni precedenti conservati;
- accesso Ingress per tutti gli utenti Home Assistant invariato (`panel_admin: false`).
