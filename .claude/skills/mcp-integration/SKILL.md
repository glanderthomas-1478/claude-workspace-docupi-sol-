---
name: MCP-Integration
description: Dieser Skill sollte verwendet werden, wenn der Benutzer nach "MCP-Server hinzufügen", "MCP integrieren", "MCP in Plugin konfigurieren", ".mcp.json verwenden", "Model Context Protocol einrichten", "externen Dienst verbinden" fragt, "${CLAUDE_PLUGIN_ROOT} mit MCP" erwähnt oder MCP-Servertypen (SSE, stdio, HTTP, WebSocket) bespricht. Bietet umfassende Anleitung zur Integration von Model Context Protocol Servern in Claude Code Plugins für externe Tool- und Service-Integration.
version: 0.1.0
---

# MCP-Integration für Claude Code Plugins

## Überblick

Das Model Context Protocol (MCP) ermöglicht es Claude Code Plugins, sich mit externen Diensten und APIs zu integrieren, indem es strukturierten Tool-Zugriff bereitstellt. Verwende MCP-Integration, um externe Service-Fähigkeiten als Tools innerhalb von Claude Code verfügbar zu machen.

**Kernfähigkeiten:**
- Verbindung zu externen Diensten (Datenbanken, APIs, Dateisysteme)
- Bereitstellung von 10+ zusammenhängenden Tools aus einem einzelnen Dienst
- Handhabung von OAuth und komplexen Authentifizierungsflows
- MCP-Server mit Plugins für automatisches Setup bündeln

## MCP-Server-Konfigurationsmethoden

Plugins können MCP-Server auf zwei Arten bündeln:

### Methode 1: Dedizierte .mcp.json (Empfohlen)

Erstelle `.mcp.json` im Plugin-Root:

```json
{
  "database-tools": {
    "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
    "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
    "env": {
      "DB_URL": "${DB_URL}"
    }
  }
}
```

**Vorteile:**
- Klare Trennung der Zuständigkeiten
- Einfacher zu warten
- Besser für mehrere Server

### Methode 2: Inline in plugin.json

Füge `mcpServers`-Feld zu plugin.json hinzu:

```json
{
  "name": "mein-plugin",
  "version": "1.0.0",
  "mcpServers": {
    "plugin-api": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/api-server",
      "args": ["--port", "8080"]
    }
  }
}
```

**Vorteile:**
- Einzelne Konfigurationsdatei
- Gut für einfache Single-Server-Plugins

## MCP-Servertypen

### stdio (Lokaler Prozess)

Führe lokale MCP-Server als Kindprozesse aus. Am besten für lokale Tools und benutzerdefinierte Server.

**Konfiguration:**
```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/erlaubter/pfad"],
    "env": {
      "LOG_LEVEL": "debug"
    }
  }
}
```

**Anwendungsfälle:**
- Dateisystem-Zugriff
- Lokale Datenbankverbindungen
- Benutzerdefinierte MCP-Server
- NPM-paketierte MCP-Server

**Prozessverwaltung:**
- Claude Code startet und verwaltet den Prozess
- Kommunikation über stdin/stdout
- Beendigung wenn Claude Code beendet wird

### SSE (Server-Sent Events)

Verbindung zu gehosteten MCP-Servern mit OAuth-Unterstützung. Am besten für Cloud-Dienste.

**Konfiguration:**
```json
{
  "asana": {
    "type": "sse",
    "url": "https://mcp.asana.com/sse"
  }
}
```

**Anwendungsfälle:**
- Offizielle gehostete MCP-Server (Asana, GitHub, etc.)
- Cloud-Dienste mit MCP-Endpunkten
- OAuth-basierte Authentifizierung
- Keine lokale Installation nötig

**Authentifizierung:**
- OAuth-Flows werden automatisch behandelt
- Benutzer wird bei Erstverwendung aufgefordert
- Token-Verwaltung durch Claude Code

### HTTP (REST API)

Verbindung zu RESTful MCP-Servern mit Token-Authentifizierung.

**Konfiguration:**
```json
{
  "api-service": {
    "type": "http",
    "url": "https://api.example.com/mcp",
    "headers": {
      "Authorization": "Bearer ${API_TOKEN}",
      "X-Custom-Header": "wert"
    }
  }
}
```

**Anwendungsfälle:**
- REST-API-basierte MCP-Server
- Token-basierte Authentifizierung
- Benutzerdefinierte API-Backends
- Zustandslose Interaktionen

### WebSocket (Echtzeit)

Verbindung zu WebSocket MCP-Servern für bidirektionale Echtzeit-Kommunikation.

**Konfiguration:**
```json
{
  "realtime-service": {
    "type": "ws",
    "url": "wss://mcp.example.com/ws",
    "headers": {
      "Authorization": "Bearer ${TOKEN}"
    }
  }
}
```

**Anwendungsfälle:**
- Echtzeit-Datenstreaming
- Persistente Verbindungen
- Push-Benachrichtigungen vom Server
- Niedrige Latenzanforderungen

## Umgebungsvariablen-Expansion

Alle MCP-Konfigurationen unterstützen Umgebungsvariablen-Substitution:

**${CLAUDE_PLUGIN_ROOT}** - Plugin-Verzeichnis (immer für Portabilität verwenden):
```json
{
  "command": "${CLAUDE_PLUGIN_ROOT}/servers/mein-server"
}
```

**Benutzer-Umgebungsvariablen** - Aus der Shell des Benutzers:
```json
{
  "env": {
    "API_KEY": "${MEIN_API_KEY}",
    "DATABASE_URL": "${DB_URL}"
  }
}
```

**Best Practice:** Dokumentiere alle erforderlichen Umgebungsvariablen in der Plugin-README.

## MCP-Tool-Benennung

Wenn MCP-Server Tools bereitstellen, werden sie automatisch mit Präfix versehen:

**Format:** `mcp__plugin_<plugin-name>_<server-name>__<tool-name>`

**Beispiel:**
- Plugin: `asana`
- Server: `asana`
- Tool: `create_task`
- **Vollständiger Name:** `mcp__plugin_asana_asana__asana_create_task`

### MCP-Tools in Commands verwenden

Erlaube spezifische MCP-Tools im Command-Frontmatter vorab:

```markdown
---
allowed-tools: [
  "mcp__plugin_asana_asana__asana_create_task",
  "mcp__plugin_asana_asana__asana_search_tasks"
]
---
```

**Wildcard (sparsam verwenden):**
```markdown
---
allowed-tools: ["mcp__plugin_asana_asana__*"]
---
```

**Best Practice:** Erlaube spezifische Tools vorab, keine Wildcards, für mehr Sicherheit.

## Lifecycle-Verwaltung

**Automatischer Start:**
- MCP-Server starten, wenn das Plugin aktiviert wird
- Verbindung wird vor der ersten Tool-Nutzung hergestellt
- Neustart erforderlich bei Konfigurationsänderungen

**Lifecycle:**
1. Plugin wird geladen
2. MCP-Konfiguration wird geparst
3. Serverprozess gestartet (stdio) oder Verbindung hergestellt (SSE/HTTP/WS)
4. Tools werden entdeckt und registriert
5. Tools sind als `mcp__plugin_...__...` verfügbar

**Server anzeigen:**
Verwende den `/mcp`-Befehl, um alle Server einschließlich Plugin-bereitgestellter zu sehen.

## Authentifizierungsmuster

### OAuth (SSE/HTTP)

OAuth wird automatisch von Claude Code behandelt:

```json
{
  "type": "sse",
  "url": "https://mcp.example.com/sse"
}
```

Benutzer authentifiziert sich im Browser bei Erstverwendung. Keine zusätzliche Konfiguration nötig.

### Token-basiert (Headers)

Statische oder Umgebungsvariablen-Token:

```json
{
  "type": "http",
  "url": "https://api.example.com",
  "headers": {
    "Authorization": "Bearer ${API_TOKEN}"
  }
}
```

Dokumentiere erforderliche Umgebungsvariablen in der README.

### Umgebungsvariablen (stdio)

Konfiguration an MCP-Server übergeben:

```json
{
  "command": "python",
  "args": ["-m", "mein_mcp_server"],
  "env": {
    "DATABASE_URL": "${DB_URL}",
    "API_KEY": "${API_KEY}",
    "LOG_LEVEL": "info"
  }
}
```

## Integrationsmuster

### Muster 1: Einfacher Tool-Wrapper

Commands verwenden MCP-Tools mit Benutzerinteraktion:

```markdown
# Command: element-erstellen.md
---
allowed-tools: ["mcp__plugin_name_server__create_item"]
---

Schritte:
1. Element-Details vom Benutzer erfassen
2. mcp__plugin_name_server__create_item verwenden
3. Erstellung bestätigen
```

**Verwenden für:** Validierung oder Vorverarbeitung vor MCP-Aufrufen hinzufügen.

### Muster 2: Autonomer Agent

Agents verwenden MCP-Tools autonom:

```markdown
# Agent: daten-analysator.md

Analyse-Prozess:
1. Daten abfragen über mcp__plugin_db_server__query
2. Ergebnisse verarbeiten und analysieren
3. Erkenntnisbericht generieren
```

**Verwenden für:** Mehrstufige MCP-Workflows ohne Benutzerinteraktion.

### Muster 3: Multi-Server-Plugin

Mehrere MCP-Server integrieren:

```json
{
  "github": {
    "type": "sse",
    "url": "https://mcp.github.com/sse"
  },
  "jira": {
    "type": "sse",
    "url": "https://mcp.jira.com/sse"
  }
}
```

**Verwenden für:** Workflows über mehrere Dienste hinweg.

## Sicherheits-Best-Practices

### HTTPS/WSS verwenden

Immer sichere Verbindungen verwenden:

```json
"url": "https://mcp.example.com/sse"
"url": "http://mcp.example.com/sse"
```

### Token-Verwaltung

**MACHEN:**
- Umgebungsvariablen für Token verwenden
- Erforderliche Env-Vars in README dokumentieren
- OAuth-Flow die Authentifizierung überlassen

**NICHT MACHEN:**
- Token in der Konfiguration fest codieren
- Token in Git committen
- Token in der Dokumentation teilen

### Berechtigungseingrenzung

Nur notwendige MCP-Tools vorab erlauben:

```markdown
allowed-tools: [
  "mcp__plugin_api_server__read_data",
  "mcp__plugin_api_server__create_item"
]

allowed-tools: ["mcp__plugin_api_server__*"]
```

## Fehlerbehandlung

### Verbindungsfehler

Behandlung von MCP-Server-Nichterreichbarkeit:
- Fallback-Verhalten in Commands bereitstellen
- Benutzer über Verbindungsprobleme informieren
- Server-URL und Konfiguration prüfen

### Tool-Aufruf-Fehler

Behandlung fehlgeschlagener MCP-Operationen:
- Eingaben vor MCP-Tool-Aufrufen validieren
- Klare Fehlermeldungen bereitstellen
- Rate-Limiting und Kontingente prüfen

### Konfigurationsfehler

MCP-Konfiguration validieren:
- Server-Konnektivität während der Entwicklung testen
- JSON-Syntax validieren
- Erforderliche Umgebungsvariablen prüfen

## Performance-Überlegungen

### Lazy Loading

MCP-Server verbinden sich bei Bedarf:
- Nicht alle Server verbinden sich beim Start
- Erste Tool-Nutzung löst Verbindung aus
- Verbindungspooling wird automatisch verwaltet

### Batching

Ähnliche Anfragen wenn möglich bündeln:

```
# Gut: Einzelne Abfrage mit Filtern
tasks = search_tasks(project="X", assignee="me", limit=50)

# Vermeiden: Viele einzelne Abfragen
for id in task_ids:
    task = get_task(id)
```

## MCP-Integration testen

### Lokales Testen

1. MCP-Server in `.mcp.json` konfigurieren
2. Plugin lokal installieren (`.claude-plugin/`)
3. `/mcp` ausführen, um zu prüfen, ob der Server erscheint
4. Tool-Aufrufe in Commands testen
5. `claude --debug` Logs auf Verbindungsprobleme prüfen

### Validierungs-Checkliste

- [ ] MCP-Konfiguration ist gültiges JSON
- [ ] Server-URL ist korrekt und erreichbar
- [ ] Erforderliche Umgebungsvariablen dokumentiert
- [ ] Tools erscheinen in `/mcp`-Ausgabe
- [ ] Authentifizierung funktioniert (OAuth oder Token)
- [ ] Tool-Aufrufe aus Commands erfolgreich
- [ ] Fehlerfälle werden elegant behandelt

## Debugging

### Debug-Logging aktivieren

```bash
claude --debug
```

Suche nach:
- MCP-Server-Verbindungsversuchen
- Tool-Discovery-Logs
- Authentifizierungsflows
- Tool-Aufruf-Fehlern

### Häufige Probleme

**Server verbindet sich nicht:**
- URL prüfen
- Prüfen, ob Server läuft (stdio)
- Netzwerkverbindung prüfen
- Authentifizierungskonfiguration prüfen

**Tools nicht verfügbar:**
- Prüfen, ob Server erfolgreich verbunden
- Tool-Namen genau prüfen
- `/mcp` ausführen, um verfügbare Tools zu sehen
- Claude Code nach Konfigurationsänderungen neu starten

**Authentifizierung schlägt fehl:**
- Zwischengespeicherte Auth-Token löschen
- Erneut authentifizieren
- Token-Scopes und -Berechtigungen prüfen
- Umgebungsvariablen prüfen

## Kurzreferenz

### MCP-Servertypen

| Typ   | Transport | Am besten für          | Auth           |
|-------|-----------|------------------------|----------------|
| stdio | Prozess   | Lokale Tools, eigene Server | Env-Vars  |
| SSE   | HTTP      | Gehostete Dienste, Cloud-APIs | OAuth    |
| HTTP  | REST      | API-Backends, Token-Auth | Token        |
| ws    | WebSocket | Echtzeit, Streaming    | Token          |

### Konfigurations-Checkliste

- [ ] Servertyp angegeben (stdio/SSE/HTTP/ws)
- [ ] Typspezifische Felder vollständig (command oder url)
- [ ] Authentifizierung konfiguriert
- [ ] Umgebungsvariablen dokumentiert
- [ ] HTTPS/WSS verwendet (nicht HTTP/WS)
- [ ] ${CLAUDE_PLUGIN_ROOT} für Pfade verwendet

### Best Practices

**MACHEN:**
- ${CLAUDE_PLUGIN_ROOT} für portable Pfade verwenden
- Erforderliche Umgebungsvariablen dokumentieren
- Sichere Verbindungen verwenden (HTTPS/WSS)
- Spezifische MCP-Tools in Commands vorab erlauben
- MCP-Integration vor Veröffentlichung testen
- Verbindungs- und Tool-Fehler elegant behandeln

**NICHT MACHEN:**
- Absolute Pfade fest codieren
- Credentials in Git committen
- HTTP statt HTTPS verwenden
- Alle Tools mit Wildcards vorab erlauben
- Fehlerbehandlung überspringen
- Einrichtungsdokumentation vergessen

## Zusätzliche Ressourcen

### Referenzdateien

Für detaillierte Informationen konsultiere:

- **`references/server-types.md`** - Detaillierte Beschreibung jedes Servertyps
- **`references/authentication.md`** - Authentifizierungsmuster und OAuth
- **`references/tool-usage.md`** - Verwendung von MCP-Tools in Commands und Agents

### Beispielkonfigurationen

Funktionierende Beispiele in `examples/`:

- **`stdio-server.json`** - Lokaler stdio MCP-Server
- **`sse-server.json`** - Gehosteter SSE-Server mit OAuth
- **`http-server.json`** - REST-API mit Token-Auth

### Externe Ressourcen

- **Offizielle MCP-Dokumentation**: https://modelcontextprotocol.io/
- **Claude Code MCP-Dokumentation**: https://docs.claude.com/en/docs/claude-code/mcp
- **MCP SDK**: @modelcontextprotocol/sdk
- **Testen**: `claude --debug` und `/mcp`-Befehl verwenden

## Implementierungs-Workflow

Um MCP-Integration zu einem Plugin hinzuzufügen:

1. MCP-Servertyp wählen (stdio, SSE, HTTP, ws)
2. `.mcp.json` im Plugin-Root mit Konfiguration erstellen
3. ${CLAUDE_PLUGIN_ROOT} für alle Dateireferenzen verwenden
4. Erforderliche Umgebungsvariablen in README dokumentieren
5. Lokal mit `/mcp`-Befehl testen
6. MCP-Tools in relevanten Commands vorab erlauben
7. Authentifizierung handhaben (OAuth oder Token)
8. Fehlerfälle testen (Verbindungsfehler, Auth-Fehler)
9. MCP-Integration in Plugin-README dokumentieren

Fokus auf stdio für benutzerdefinierte/lokale Server, SSE für gehostete Dienste mit OAuth.
