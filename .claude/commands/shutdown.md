# Shutdown

> Session sauber beenden: Workspace scannen, aufräumen, alles auf den neuesten Stand bringen, committen und pushen.

## Instructions

Führe die folgenden Schritte der Reihe nach aus. Überspringe keinen Schritt.

### Schritt 1: Workspace scannen

1. Lies `CLAUDE.md` — prüfe, ob die dokumentierte Struktur noch stimmt
2. Scanne alle Verzeichnisse:
   - `context/` — Sind alle Dateien aktuell? Gibt es veraltete Einträge?
   - `plans/` — Gibt es Pläne mit Status "Draft", die auf "Implemented" stehen sollten?
   - `outputs/` — Gibt es temporäre oder verwaiste Dateien?
   - `scripts/` — Gibt es unbenutzte Skripte?
   - `reference/` — Gibt es veraltete Referenzdokumente?
3. Prüfe auf Dateien, die nicht in die Struktur gehören (z.B. .DS_Store, temp files, __pycache__, .pyc, logs)

### Schritt 2: Aufräumen

1. Lösche offensichtlich unnötige Dateien:
   - `.DS_Store` Dateien
   - `__pycache__/` Verzeichnisse
   - `.pyc` Dateien
   - Temporäre Dateien (*.tmp, *.bak, *.log)
2. Für Dateien, bei denen unklar ist ob sie gebraucht werden: **NICHT löschen**, sondern in der Zusammenfassung auflisten und den User fragen

### Schritt 3: CLAUDE.md aktualisieren

Prüfe ob CLAUDE.md Änderungen braucht:
- Neue Dateien/Ordner, die nicht dokumentiert sind?
- Entfernte Dateien/Ordner, die noch dokumentiert sind?
- Neue Commands, Skripte oder Workflows, die aufgelistet werden müssen?
- Offene Punkte, die erledigt wurden und abgehakt werden können?

Falls ja: Aktualisiere CLAUDE.md.

### Schritt 4: Context-Dateien prüfen

Prüfe jede Datei in `context/`:
- Stimmen die Informationen noch mit dem überein, was in dieser Session passiert ist?
- Gibt es neue Erkenntnisse, die festgehalten werden sollten?

Falls ja: Aktualisiere die betreffenden Dateien.

### Schritt 5: Git — Committen und Pushen

1. `git status` — Was hat sich geändert?
2. Stage alle relevanten Änderungen (KEINE Secrets, KEINE .env)
3. Commit mit beschreibender Message: "Shutdown: [was aufgeräumt/aktualisiert wurde]"
4. Push auf Remote

### Schritt 6: Zusammenfassung

Liefere einen kurzen Report:

1. **Aufgeräumt:** Welche Dateien wurden gelöscht oder bereinigt?
2. **Aktualisiert:** Welche Dateien wurden auf den neuesten Stand gebracht?
3. **Offen:** Was konnte nicht automatisch erledigt werden? (Fragen an den User)
4. **Nächste Session:** Was sollte als nächstes angegangen werden?

### Schritt 7: Verabschiedung

Verabschiede dich persönlich und freundlich vom Benutzer. Fasse kurz zusammen, was ihr in dieser Session gemeinsam erreicht habt, und wünsche einen guten Tag/Abend. Halte den Ton warm aber professionell — wie ein guter Kollege, der Feierabend macht. Warte auf die Antwort des Benutzers, damit er sich auch verabschieden kann, bevor die Session endet.
