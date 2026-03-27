# Shell-Aliase für Claude Code

Zwei Shell-Aliase vereinfachen den Start von Claude Code Sessions mit diesem Workspace.

## Einrichtung

Füge diese Zeilen zu deiner `~/.zshrc` (oder `~/.bashrc`) hinzu:

```bash
alias cs='claude "/prime"'
alias cr='claude --dangerously-skip-permissions "/prime"'
```

Dann Shell neu laden: `source ~/.zshrc`

## Die Aliase

### `cs` — Claude Sicher

```bash
alias cs='claude "/prime"'
```

Startet Claude Code und führt sofort `/prime` aus, um den Workspace-Kontext zu laden. Claude wird um Erlaubnis fragen, bevor er Commands ausführt, sensible Dateien liest oder Änderungen vornimmt.

**Verwenden, wenn:** Du eine neue Session startest, in der du jede Aktion überprüfen und genehmigen möchtest.

### `cr` — Claude Run

```bash
alias cr='claude --dangerously-skip-permissions "/prime"'
```

Startet Claude Code mit deaktivierten Berechtigungsabfragen und führt dann `/prime` aus. Claude kann Commands ausführen und Änderungen vornehmen, ohne um Genehmigung zu fragen.

**Verwenden, wenn:** Du der Aufgabe vertraust, schnellere Iteration möchtest oder Routinearbeit erledigst, bei der ständige Genehmigungen dich ausbremsen.

## Warum beides?

- **`cs`** gibt dir Kontrolle — gut für unbekannte Aufgaben, sensible Operationen oder wenn du lernen möchtest, was Claude tut
- **`cr`** gibt dir Geschwindigkeit — gut für vertraute Workflows, in denen du Claude vertraust, autonom zu arbeiten

Beide führen `/prime` automatisch aus, sodass Claude jede Session vollständig orientiert an deinem Workspace, deinen Zielen und deinem Kontext startet.
