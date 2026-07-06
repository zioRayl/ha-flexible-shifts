# Release 0.1.1 - Correzione avvio Home Assistant

Questa versione corregge il crash all'avvio osservato su Home Assistant con Python 3.14 e FastAPI 0.115.12.

## Correzione

Gli endpoint DELETE per utenti, turni e ferie erano dichiarati con stato HTTP 204, ma lasciavano a FastAPI la response class predefinita. La combinazione causava l'errore:

```text
AssertionError: Status code 204 must not have a response body
```

Ora tutti gli endpoint restituiscono esplicitamente `Response(status_code=204)` e dichiarano `response_class=Response`.

## Installazione

Aggiornare il repository GitHub con questi file, quindi ricostruire/reinstallare l'add-on alla versione 0.1.1.
