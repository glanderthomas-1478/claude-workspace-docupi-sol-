# MCP-Servertypen: Detaillierte Referenz

Vollständige Referenz für alle MCP-Servertypen, die in Claude Code Plugins unterstützt werden.

## stdio (Standard Input/Output)

### Überblick

Führe lokale MCP-Server als Kindprozesse mit Kommunikation über stdin/stdout aus. Beste Wahl für lokale Tools, benutzerdefinierte Server und NPM-Pakete.

### Konfiguration

**Einfach:**
```json
{
  "mein-server": {
    "command": "npx",
    "args": ["-y", "mein-mcp-server"]
  }
}
```

**Mit Umgebung:**
```json
{
  "mein-server": {
    "command": "${CLAUDE_PLUGIN_ROOT}/servers/eigener-server",
    "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
    "env": {
      "API_KEY": "${MEIN_API_KEY}",
      "LOG_LEVEL": "debug",
      "DATABASE_URL": "${DB_URL}"
    }
  }
}
```

### Prozess-Lifecycle

1. **Start**: Claude Code startet Prozess mit `command` und `args`
2. **Kommunikation**: JSON-RPC-Nachrichten über stdin/stdout
3. **Lebensdauer**: Prozess läuft während der gesamten Claude Code Session
4. **Beendigung**: Prozess wird beendet, wenn Claude Code beendet wird

### Anwendungsfälle

**NPM-Pakete:**
```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/pfad"]
  }
}
```

**Eigene Skripte:**
```json
{
  "eigener": {
    "command": "${CLAUDE_PLUGIN_ROOT}/servers/mein-server.js",
    "args": ["--verbose"]
  }
}
```

**Python-Server:**
```json
{
  "python-server": {
    "command": "python",
    "args": ["-m", "mein_mcp_server"],
    "env": {
      "PYTHONUNBUFFERED": "1"
    }
  }
}
```

### Best Practices

1. **Absolute Pfade oder ${CLAUDE_PLUGIN_ROOT} verwenden**
2. **PYTHONUNBUFFERED für Python-Server setzen**
3. **Konfiguration über Args oder Env übergeben, nicht über stdin**
4. **Server-Abstürze elegant behandeln**
5. **Auf stderr loggen, nicht stdout (stdout ist für das MCP-Protokoll)**

### Fehlerbehebung

**Server startet nicht:**
- Prüfen, ob Befehl existiert und ausführbar ist
- Dateipfade prüfen
- Berechtigungen prüfen
- `claude --debug` Logs prüfen

**Kommunikation schlägt fehl:**
- Sicherstellen, dass Server stdin/stdout korrekt verwendet
- Auf versehentliche print/console.log-Ausgaben prüfen
- JSON-RPC-Format prüfen

## SSE (Server-Sent Events)

### Überblick

Verbindung zu gehosteten MCP-Servern über HTTP mit Server-Sent Events für Streaming. Am besten für Cloud-Dienste und OAuth-Authentifizierung.

### Konfiguration

**Einfach:**
```json
{
  "gehosteter-dienst": {
    "type": "sse",
    "url": "https://mcp.example.com/sse"
  }
}
```

**Mit Headers:**
```json
{
  "dienst": {
    "type": "sse",
    "url": "https://mcp.example.com/sse",
    "headers": {
      "X-API-Version": "v1",
      "X-Client-ID": "${CLIENT_ID}"
    }
  }
}
```

### Verbindungs-Lifecycle

1. **Initialisierung**: HTTP-Verbindung zur URL hergestellt
2. **Handshake**: MCP-Protokoll-Aushandlung
3. **Streaming**: Server sendet Events über SSE
4. **Anfragen**: Client sendet HTTP POST für Tool-Aufrufe
5. **Wiederverbindung**: Automatische Wiederverbindung bei Trennung

### Authentifizierung

**OAuth (Automatisch):**
```json
{
  "asana": {
    "type": "sse",
    "url": "https://mcp.asana.com/sse"
  }
}
```

Claude Code behandelt den OAuth-Flow:
1. Benutzer wird bei Erstverwendung zur Authentifizierung aufgefordert
2. Öffnet Browser für OAuth-Flow
3. Token werden sicher gespeichert
4. Automatische Token-Erneuerung

**Benutzerdefinierte Headers:**
```json
{
  "dienst": {
    "type": "sse",
    "url": "https://mcp.example.com/sse",
    "headers": {
      "Authorization": "Bearer ${API_TOKEN}"
    }
  }
}
```

### Anwendungsfälle

**Offizielle Dienste:**
- Asana: `https://mcp.asana.com/sse`
- GitHub: `https://mcp.github.com/sse`
- Andere gehostete MCP-Server

**Eigene gehostete Server:**
Eigenen MCP-Server deployen und über HTTPS + SSE exponieren.

### Best Practices

1. **Immer HTTPS verwenden, nie HTTP**
2. **OAuth die Authentifizierung überlassen, wenn verfügbar**
3. **Umgebungsvariablen für Token verwenden**
4. **Verbindungsfehler elegant behandeln**
5. **Erforderliche OAuth-Scopes dokumentieren**

### Fehlerbehebung

**Verbindung abgelehnt:**
- URL prüfen
- HTTPS-Zertifikat prüfen
- Netzwerkverbindung prüfen
- Firewall-Einstellungen prüfen

**OAuth schlägt fehl:**
- Zwischengespeicherte Token löschen
- OAuth-Scopes prüfen
- Redirect-URLs prüfen
- Erneut authentifizieren

## HTTP (REST API)

### Überblick

Verbindung zu RESTful MCP-Servern über Standard-HTTP-Anfragen. Am besten für Token-basierte Auth und zustandslose Interaktionen.

### Konfiguration

**Einfach:**
```json
{
  "api": {
    "type": "http",
    "url": "https://api.example.com/mcp"
  }
}
```

**Mit Authentifizierung:**
```json
{
  "api": {
    "type": "http",
    "url": "https://api.example.com/mcp",
    "headers": {
      "Authorization": "Bearer ${API_TOKEN}",
      "Content-Type": "application/json",
      "X-API-Version": "2024-01-01"
    }
  }
}
```

### Anfrage-/Antwort-Flow

1. **Tool-Discovery**: GET zum Entdecken verfügbarer Tools
2. **Tool-Aufruf**: POST mit Tool-Name und Parametern
3. **Antwort**: JSON-Antwort mit Ergebnissen oder Fehlern
4. **Zustandslos**: Jede Anfrage unabhängig

### Authentifizierung

**Token-basiert:**
```json
{
  "headers": {
    "Authorization": "Bearer ${API_TOKEN}"
  }
}
```

**API-Schlüssel:**
```json
{
  "headers": {
    "X-API-Key": "${API_KEY}"
  }
}
```

**Benutzerdefinierte Auth:**
```json
{
  "headers": {
    "X-Auth-Token": "${AUTH_TOKEN}",
    "X-User-ID": "${USER_ID}"
  }
}
```

### Anwendungsfälle

- REST-API-Backends
- Interne Dienste
- Microservices
- Serverless Functions

### Best Practices

1. **HTTPS für alle Verbindungen verwenden**
2. **Token in Umgebungsvariablen speichern**
3. **Retry-Logik für vorübergehende Fehler implementieren**
4. **Rate-Limiting behandeln**
5. **Angemessene Timeouts setzen**

### Fehlerbehebung

**HTTP-Fehler:**
- 401: Authentifizierungs-Header prüfen
- 403: Berechtigungen prüfen
- 429: Rate-Limiting implementieren
- 500: Server-Logs prüfen

**Timeout-Probleme:**
- Timeout bei Bedarf erhöhen
- Server-Performance prüfen
- Tool-Implementierungen optimieren

## WebSocket (Echtzeit)

### Überblick

Verbindung zu MCP-Servern über WebSocket für bidirektionale Echtzeit-Kommunikation. Am besten für Streaming und Anwendungen mit niedriger Latenz.

### Konfiguration

**Einfach:**
```json
{
  "realtime": {
    "type": "ws",
    "url": "wss://mcp.example.com/ws"
  }
}
```

**Mit Authentifizierung:**
```json
{
  "realtime": {
    "type": "ws",
    "url": "wss://mcp.example.com/ws",
    "headers": {
      "Authorization": "Bearer ${TOKEN}",
      "X-Client-ID": "${CLIENT_ID}"
    }
  }
}
```

### Verbindungs-Lifecycle

1. **Handshake**: WebSocket-Upgrade-Anfrage
2. **Verbindung**: Persistenter bidirektionaler Kanal
3. **Nachrichten**: JSON-RPC über WebSocket
4. **Heartbeat**: Keep-Alive-Nachrichten
5. **Wiederverbindung**: Automatisch bei Trennung

### Anwendungsfälle

- Echtzeit-Datenstreaming
- Live-Updates und Benachrichtigungen
- Kollaboratives Bearbeiten
- Tool-Aufrufe mit niedriger Latenz
- Push-Benachrichtigungen vom Server

### Best Practices

1. **WSS (sicheres WebSocket) verwenden, nie WS**
2. **Heartbeat/Ping-Pong implementieren**
3. **Wiederverbindungslogik implementieren**
4. **Nachrichten während der Trennung puffern**
5. **Verbindungs-Timeouts setzen**

### Fehlerbehebung

**Verbindungsabbrüche:**
- Wiederverbindungslogik implementieren
- Netzwerkstabilität prüfen
- Prüfen, ob Server WebSocket unterstützt
- Firewall-Einstellungen prüfen

**Nachrichtenübermittlung:**
- Nachrichtenbestätigung implementieren
- Ungeordnete Nachrichten behandeln
- Während Trennung puffern

## Vergleichsmatrix

| Merkmal | stdio | SSE | HTTP | WebSocket |
|---------|-------|-----|------|-----------|
| **Transport** | Prozess | HTTP/SSE | HTTP | WebSocket |
| **Richtung** | Bidirektional | Server→Client | Anfrage/Antwort | Bidirektional |
| **Zustand** | Zustandsbehaftet | Zustandsbehaftet | Zustandslos | Zustandsbehaftet |
| **Auth** | Env-Vars | OAuth/Headers | Headers | Headers |
| **Anwendungsfall** | Lokale Tools | Cloud-Dienste | REST-APIs | Echtzeit |
| **Latenz** | Niedrigste | Mittel | Mittel | Niedrig |
| **Einrichtung** | Einfach | Mittel | Einfach | Mittel |
| **Wiederverbindung** | Prozess-Neustart | Automatisch | N/A | Automatisch |

## Den richtigen Typ wählen

**stdio verwenden, wenn:**
- Lokale Tools oder eigene Server ausgeführt werden
- Niedrigste Latenz benötigt wird
- Mit Dateisystemen oder lokalen Datenbanken gearbeitet wird
- Server mit Plugin ausgeliefert wird

**SSE verwenden, wenn:**
- Verbindung zu gehosteten Diensten
- OAuth-Authentifizierung benötigt wird
- Offizielle MCP-Server verwendet werden (Asana, GitHub)
- Automatische Wiederverbindung gewünscht

**HTTP verwenden, wenn:**
- Integration mit REST-APIs
- Zustandslose Interaktionen benötigt
- Token-basierte Auth verwendet wird
- Einfaches Anfrage/Antwort-Muster

**WebSocket verwenden, wenn:**
- Echtzeit-Updates benötigt
- Kollaborative Features gebaut werden
- Niedrige Latenz kritisch
- Bidirektionales Streaming erforderlich

## Migration zwischen Typen

### Von stdio zu SSE

**Vorher (stdio):**
```json
{
  "lokaler-server": {
    "command": "node",
    "args": ["server.js"]
  }
}
```

**Nachher (SSE - Server deployen):**
```json
{
  "gehosteter-server": {
    "type": "sse",
    "url": "https://mcp.example.com/sse"
  }
}
```

### Von HTTP zu WebSocket

**Vorher (HTTP):**
```json
{
  "api": {
    "type": "http",
    "url": "https://api.example.com/mcp"
  }
}
```

**Nachher (WebSocket):**
```json
{
  "realtime": {
    "type": "ws",
    "url": "wss://api.example.com/ws"
  }
}
```

Vorteile: Echtzeit-Updates, niedrigere Latenz, bidirektionale Kommunikation.

## Erweiterte Konfiguration

### Mehrere Server

Verschiedene Typen kombinieren:

```json
{
  "lokale-db": {
    "command": "npx",
    "args": ["-y", "mcp-server-sqlite", "./daten.db"]
  },
  "cloud-api": {
    "type": "sse",
    "url": "https://mcp.example.com/sse"
  },
  "interner-dienst": {
    "type": "http",
    "url": "https://api.example.com/mcp",
    "headers": {
      "Authorization": "Bearer ${API_TOKEN}"
    }
  }
}
```

### Bedingte Konfiguration

Umgebungsvariablen zum Serverwechsel verwenden:

```json
{
  "api": {
    "type": "http",
    "url": "${API_URL}",
    "headers": {
      "Authorization": "Bearer ${API_TOKEN}"
    }
  }
}
```

Verschiedene Werte für Dev/Prod setzen:
- Dev: `API_URL=http://localhost:8080/mcp`
- Prod: `API_URL=https://api.production.com/mcp`

## Sicherheitsüberlegungen

### stdio-Sicherheit

- Befehlspfade validieren
- Keine benutzerbereitgestellten Befehle ausführen
- Umgebungsvariablen-Zugriff einschränken
- Dateisystem-Zugriff beschränken

### Netzwerksicherheit

- Immer HTTPS/WSS verwenden
- SSL-Zertifikate validieren
- Zertifikatsüberprüfung nicht überspringen
- Sichere Token-Speicherung verwenden

### Token-Verwaltung

- Token nie fest codieren
- Umgebungsvariablen verwenden
- Token regelmäßig rotieren
- Token-Erneuerung implementieren
- Erforderliche Scopes dokumentieren

## Fazit

Wähle den MCP-Servertyp basierend auf deinem Anwendungsfall:
- **stdio** für lokale, eigene oder NPM-paketierte Server
- **SSE** für gehostete Dienste mit OAuth
- **HTTP** für REST-APIs mit Token-Auth
- **WebSocket** für bidirektionale Echtzeit-Kommunikation

Teste gründlich und behandle Fehler elegant für robuste MCP-Integration.
