# MCP-Tools in Commands und Agents verwenden

Vollständiger Leitfaden zur effektiven Nutzung von MCP-Tools in Claude Code Plugin-Commands und -Agents.

## Überblick

Sobald ein MCP-Server konfiguriert ist, werden seine Tools mit dem Präfix `mcp__plugin_<plugin-name>_<server-name>__<tool-name>` verfügbar. Verwende diese Tools in Commands und Agents wie die eingebauten Claude Code Tools.

## Tool-Namenskonvention

### Format

```
mcp__plugin_<plugin-name>_<server-name>__<tool-name>
```

### Beispiele

**Asana-Plugin mit Asana-Server:**
- `mcp__plugin_asana_asana__asana_create_task`
- `mcp__plugin_asana_asana__asana_search_tasks`
- `mcp__plugin_asana_asana__asana_get_project`

**Eigenes Plugin mit Datenbank-Server:**
- `mcp__plugin_meinplug_database__query`
- `mcp__plugin_meinplug_database__execute`
- `mcp__plugin_meinplug_database__list_tables`

### Tool-Namen entdecken

**Verwende den `/mcp`-Befehl:**
```bash
/mcp
```

Dies zeigt:
- Alle verfügbaren MCP-Server
- Von jedem Server bereitgestellte Tools
- Tool-Schemas und Beschreibungen
- Vollständige Tool-Namen für die Konfiguration

## Tools in Commands verwenden

### Tools vorab erlauben

MCP-Tools im Command-Frontmatter angeben:

```markdown
---
description: Neue Asana-Aufgabe erstellen
allowed-tools: [
  "mcp__plugin_asana_asana__asana_create_task"
]
---

# Aufgabe-erstellen-Command

Um eine Aufgabe zu erstellen:
1. Aufgabendetails vom Benutzer erfassen
2. mcp__plugin_asana_asana__asana_create_task mit den Details verwenden
3. Erstellung dem Benutzer bestätigen
```

### Mehrere Tools

```markdown
---
allowed-tools: [
  "mcp__plugin_asana_asana__asana_create_task",
  "mcp__plugin_asana_asana__asana_search_tasks",
  "mcp__plugin_asana_asana__asana_get_project"
]
---
```

### Wildcard (Sparsam verwenden)

```markdown
---
allowed-tools: ["mcp__plugin_asana_asana__*"]
---
```

**Vorsicht:** Nur Wildcards verwenden, wenn der Command wirklich Zugriff auf alle Tools eines Servers benötigt.

### Tool-Nutzung in Command-Anweisungen

**Beispiel-Command:**
```markdown
---
description: Asana-Aufgaben suchen und erstellen
allowed-tools: [
  "mcp__plugin_asana_asana__asana_search_tasks",
  "mcp__plugin_asana_asana__asana_create_task"
]
---

# Asana-Aufgabenverwaltung

## Aufgaben suchen

Um nach Aufgaben zu suchen:
1. mcp__plugin_asana_asana__asana_search_tasks verwenden
2. Suchfilter angeben (Zugewiesener, Projekt, etc.)
3. Ergebnisse dem Benutzer anzeigen

## Aufgaben erstellen

Um eine Aufgabe zu erstellen:
1. Aufgabendetails erfassen:
   - Titel (erforderlich)
   - Beschreibung
   - Projekt
   - Zugewiesener
   - Fälligkeitsdatum
2. mcp__plugin_asana_asana__asana_create_task verwenden
3. Bestätigung mit Aufgaben-Link anzeigen
```

## Tools in Agents verwenden

### Agent-Konfiguration

Agents können MCP-Tools autonom ohne vorheriges Erlauben verwenden:

```markdown
---
name: asana-status-updater
description: Dieser Agent sollte verwendet werden, wenn der Benutzer nach "Asana-Status aktualisieren", "Projektbericht generieren" oder "Asana-Aufgaben synchronisieren" fragt
model: inherit
color: blue
---

## Rolle

Autonomer Agent zur Generierung von Asana-Projekt-Statusberichten.

## Prozess

1. **Aufgaben abfragen**: mcp__plugin_asana_asana__asana_search_tasks verwenden, um alle Aufgaben zu erhalten
2. **Fortschritt analysieren**: Abschlussraten berechnen und Blocker identifizieren
3. **Bericht generieren**: Formatierten Status-Update erstellen
4. **Asana aktualisieren**: mcp__plugin_asana_asana__asana_create_comment verwenden, um Bericht zu posten

## Verfügbare Tools

Der Agent hat Zugriff auf alle Asana MCP-Tools ohne vorherige Genehmigung.
```

### Agent-Tool-Zugriff

Agents haben breiteren Tool-Zugriff als Commands:
- Können jedes Tool verwenden, das Claude als notwendig erachtet
- Benötigen keine vorab erlaubten Listen
- Sollten dokumentieren, welche Tools sie typischerweise verwenden

## Tool-Aufrufmuster

### Muster 1: Einfacher Tool-Aufruf

Einzelner Tool-Aufruf mit Validierung:

```markdown
Schritte:
1. Validieren, dass der Benutzer erforderliche Felder angegeben hat
2. mcp__plugin_api_server__create_item mit validierten Daten aufrufen
3. Auf Fehler prüfen
4. Bestätigung anzeigen
```

### Muster 2: Sequenzielle Tools

Mehrere Tool-Aufrufe verketten:

```markdown
Schritte:
1. Nach bestehenden Elementen suchen: mcp__plugin_api_server__search
2. Wenn nicht gefunden, neu erstellen: mcp__plugin_api_server__create
3. Metadaten hinzufügen: mcp__plugin_api_server__update_metadata
4. Endgültige Element-ID zurückgeben
```

### Muster 3: Batch-Operationen

Mehrere Aufrufe mit demselben Tool:

```markdown
Schritte:
1. Liste der zu verarbeitenden Elemente holen
2. Für jedes Element:
   - mcp__plugin_api_server__update_item aufrufen
   - Erfolg/Fehler tracken
3. Ergebniszusammenfassung berichten
```

### Muster 4: Fehlerbehandlung

Elegante Fehlerbehandlung:

```markdown
Schritte:
1. Versuche mcp__plugin_api_server__get_data aufzurufen
2. Bei Fehler (Rate-Limit, Netzwerk, etc.):
   - Warten und erneut versuchen (max. 3 Versuche)
   - Bei weiterem Fehlschlag Benutzer informieren
   - Konfigurationsprüfung vorschlagen
3. Bei Erfolg Daten verarbeiten
```

## Tool-Parameter

### Tool-Schemas verstehen

Jedes MCP-Tool hat ein Schema, das seine Parameter definiert. Mit `/mcp` anzeigen.

**Beispiel-Schema:**
```json
{
  "name": "asana_create_task",
  "description": "Neue Asana-Aufgabe erstellen",
  "inputSchema": {
    "type": "object",
    "properties": {
      "name": {
        "type": "string",
        "description": "Aufgabentitel"
      },
      "notes": {
        "type": "string",
        "description": "Aufgabenbeschreibung"
      },
      "workspace": {
        "type": "string",
        "description": "Workspace-GID"
      }
    },
    "required": ["name", "workspace"]
  }
}
```

### Tools mit Parametern aufrufen

Claude strukturiert Tool-Aufrufe automatisch basierend auf dem Schema:

```typescript
// Claude generiert dies intern
{
  toolName: "mcp__plugin_asana_asana__asana_create_task",
  input: {
    name: "PR #123 reviewen",
    notes: "Code-Review für neues Feature",
    workspace: "12345",
    assignee: "67890",
    due_on: "2025-01-15"
  }
}
```

### Parameter-Validierung

**In Commands vor dem Aufruf validieren:**

```markdown
Schritte:
1. Erforderliche Parameter prüfen:
   - Titel ist nicht leer
   - Workspace-ID ist angegeben
   - Fälligkeitsdatum hat gültiges Format (YYYY-MM-DD)
2. Bei fehlgeschlagener Validierung Benutzer auffordern, fehlende Daten anzugeben
3. Bei bestandener Validierung MCP-Tool aufrufen
4. Tool-Fehler elegant behandeln
```

## Antwortbehandlung

### Erfolgreiche Antworten

```markdown
Schritte:
1. MCP-Tool aufrufen
2. Bei Erfolg:
   - Relevante Daten aus Antwort extrahieren
   - Für Benutzeranzeige formatieren
   - Bestätigungsnachricht bereitstellen
   - Relevante Links oder IDs einschließen
```

### Fehlerantworten

```markdown
Schritte:
1. MCP-Tool aufrufen
2. Bei Fehler:
   - Fehlertyp prüfen (Auth, Rate-Limit, Validierung, etc.)
   - Hilfreiche Fehlermeldung bereitstellen
   - Behebungsschritte vorschlagen
   - Keine internen Fehlerdetails dem Benutzer zeigen
```

### Teilerfolg

```markdown
Schritte:
1. Batch-Operation mit mehreren MCP-Aufrufen
2. Erfolge und Fehler separat tracken
3. Zusammenfassung berichten:
   - "8 von 10 Elementen erfolgreich verarbeitet"
   - "Fehlgeschlagene Elemente: [element1, element2] wegen [Grund]"
   - Erneuten Versuch oder manuelle Intervention vorschlagen
```

## Performance-Optimierung

### Anfragen bündeln

**Gut: Einzelne Abfrage mit Filtern**
```markdown
Schritte:
1. mcp__plugin_api_server__search mit Filtern aufrufen:
   - project_id: "123"
   - status: "active"
   - limit: 100
2. Alle Ergebnisse verarbeiten
```

**Vermeiden: Viele einzelne Abfragen**
```markdown
Schritte:
1. Für jede Element-ID:
   - mcp__plugin_api_server__get_item aufrufen
   - Element verarbeiten
```

### Ergebnisse zwischenspeichern

```markdown
Schritte:
1. Aufwändige MCP-Operation aufrufen: mcp__plugin_api_server__analyze
2. Ergebnisse in Variable zur Wiederverwendung speichern
3. Zwischengespeicherte Ergebnisse für nachfolgende Operationen verwenden
4. Nur bei Datenänderung erneut abrufen
```

### Parallele Tool-Aufrufe

Wenn Tools nicht voneinander abhängen, parallel aufrufen:

```markdown
Schritte:
1. Parallele Aufrufe (Claude handhabt dies automatisch):
   - mcp__plugin_api_server__get_project
   - mcp__plugin_api_server__get_users
   - mcp__plugin_api_server__get_tags
2. Auf Abschluss aller warten
3. Ergebnisse kombinieren
```

## Integrations-Best-Practices

### Benutzererlebnis

**Feedback geben:**
```markdown
Schritte:
1. Benutzer informieren: "Suche Asana-Aufgaben..."
2. mcp__plugin_asana_asana__asana_search_tasks aufrufen
3. Fortschritt zeigen: "15 Aufgaben gefunden, analysiere..."
4. Ergebnisse präsentieren
```

**Lange Operationen behandeln:**
```markdown
Schritte:
1. Benutzer warnen: "Dies kann eine Minute dauern..."
2. In kleinere Schritte mit Updates aufteilen
3. Inkrementellen Fortschritt zeigen
4. Abschlusszusammenfassung am Ende
```

### Fehlermeldungen

**Gute Fehlermeldungen:**
```
"Aufgabe konnte nicht erstellt werden. Bitte prüfe:
   1. Du bist bei Asana angemeldet
   2. Du hast Zugriff auf Workspace 'Engineering'
   3. Das Projekt 'Q1-Ziele' existiert"
```

**Schlechte Fehlermeldungen:**
```
"Fehler: MCP-Tool hat 403 zurückgegeben"
```

### Dokumentation

**MCP-Tool-Nutzung im Command dokumentieren:**
```markdown
## Verwendete MCP-Tools

Dieser Command verwendet folgende Asana MCP-Tools:
- **asana_search_tasks**: Aufgaben nach Kriterien suchen
- **asana_create_task**: Neue Aufgabe mit Details erstellen
- **asana_update_task**: Bestehende Aufgabeneigenschaften aktualisieren

Stelle sicher, dass du bei Asana authentifiziert bist, bevor du diesen Command ausführst.
```

## Tool-Nutzung testen

### Lokales Testen

1. **MCP-Server** in `.mcp.json` konfigurieren
2. **Plugin lokal installieren** in `.claude-plugin/`
3. **Tools prüfen** mit `/mcp`
4. **Command testen**, der Tools verwendet
5. **Debug-Ausgabe prüfen**: `claude --debug`

### Testszenarien

**Erfolgreiche Aufrufe testen:**
```markdown
Schritte:
1. Testdaten im externen Dienst erstellen
2. Command ausführen, der diese Daten abfragt
3. Prüfen, ob korrekte Ergebnisse zurückgegeben werden
```

**Fehlerfälle testen:**
```markdown
Schritte:
1. Mit fehlender Authentifizierung testen
2. Mit ungültigen Parametern testen
3. Mit nicht existierenden Ressourcen testen
4. Prüfen, ob elegante Fehlerbehandlung funktioniert
```

**Grenzfälle testen:**
```markdown
Schritte:
1. Mit leeren Ergebnissen testen
2. Mit maximalen Ergebnissen testen
3. Mit Sonderzeichen testen
4. Mit gleichzeitigem Zugriff testen
```

## Häufige Muster

### Muster: CRUD-Operationen

```markdown
---
allowed-tools: [
  "mcp__plugin_api_server__create_item",
  "mcp__plugin_api_server__read_item",
  "mcp__plugin_api_server__update_item",
  "mcp__plugin_api_server__delete_item"
]
---

# Elementverwaltung

## Erstellen
create_item mit erforderlichen Feldern verwenden...

## Lesen
read_item mit Element-ID verwenden...

## Aktualisieren
update_item mit Element-ID und Änderungen verwenden...

## Löschen
delete_item mit Element-ID verwenden (vorher Bestätigung einholen)...
```

### Muster: Suchen und Verarbeiten

```markdown
Schritte:
1. **Suchen**: mcp__plugin_api_server__search mit Filtern
2. **Filtern**: Bei Bedarf zusätzliche lokale Filterung anwenden
3. **Transformieren**: Jedes Ergebnis verarbeiten
4. **Präsentieren**: Formatieren und dem Benutzer anzeigen
```

### Muster: Mehrstufiger Workflow

```markdown
Schritte:
1. **Vorbereitung**: Alle erforderlichen Informationen sammeln
2. **Validierung**: Datenvollständigkeit prüfen
3. **Ausführung**: Kette von MCP-Tool-Aufrufen:
   - Übergeordnete Ressource erstellen
   - Untergeordnete Ressourcen erstellen
   - Ressourcen verknüpfen
   - Metadaten hinzufügen
4. **Überprüfung**: Bestätigen, dass alle Schritte erfolgreich waren
5. **Bericht**: Zusammenfassung dem Benutzer bereitstellen
```

## Fehlerbehebung

### Tools nicht verfügbar

**Prüfen:**
- MCP-Server korrekt konfiguriert
- Server verbunden (mit `/mcp` prüfen)
- Tool-Namen stimmen exakt überein (Groß-/Kleinschreibung)
- Claude Code nach Konfigurationsänderungen neu starten

### Tool-Aufrufe schlagen fehl

**Prüfen:**
- Authentifizierung gültig
- Parameter entsprechen Tool-Schema
- Erforderliche Parameter angegeben
- `claude --debug` Logs prüfen

### Performance-Probleme

**Prüfen:**
- Abfragen bündeln statt einzeln aufrufen
- Ergebnisse bei Bedarf zwischenspeichern
- Keine unnötigen Tool-Aufrufe machen
- Parallele Aufrufe wenn möglich

## Fazit

Effektive MCP-Tool-Nutzung erfordert:
1. **Tool-Schemas verstehen** über `/mcp`
2. **Tools in Commands** angemessen vorab erlauben
3. **Fehler elegant behandeln**
4. **Performance optimieren** mit Batching und Caching
5. **Gute UX bieten** mit Feedback und klaren Fehlern
6. **Gründlich testen** vor dem Deployment

Befolge diese Muster für robuste MCP-Tool-Integration in deinen Plugin-Commands und -Agents.
