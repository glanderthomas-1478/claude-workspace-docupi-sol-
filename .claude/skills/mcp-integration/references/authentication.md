# MCP-Authentifizierungsmuster

Vollständiger Leitfaden zu Authentifizierungsmethoden für MCP-Server in Claude Code Plugins.

## Überblick

MCP-Server unterstützen mehrere Authentifizierungsmethoden je nach Servertyp und Service-Anforderungen. Wähle die Methode, die am besten zu deinem Anwendungsfall und deinen Sicherheitsanforderungen passt.

## OAuth (Automatisch)

### Funktionsweise

Claude Code behandelt den vollständigen OAuth 2.0 Flow für SSE- und HTTP-Server automatisch:

1. Benutzer versucht MCP-Tool zu verwenden
2. Claude Code erkennt, dass Authentifizierung nötig ist
3. Öffnet Browser für OAuth-Zustimmung
4. Benutzer autorisiert im Browser
5. Token werden sicher von Claude Code gespeichert
6. Automatische Token-Erneuerung

### Konfiguration

```json
{
  "service": {
    "type": "sse",
    "url": "https://mcp.example.com/sse"
  }
}
```

Keine zusätzliche Auth-Konfiguration nötig! Claude Code erledigt alles.

### Unterstützte Dienste

**Bekannte OAuth-fähige MCP-Server:**
- Asana: `https://mcp.asana.com/sse`
- GitHub (wenn verfügbar)
- Google-Dienste (wenn verfügbar)
- Benutzerdefinierte OAuth-Server

### OAuth-Scopes

OAuth-Scopes werden vom MCP-Server bestimmt. Benutzer sehen die erforderlichen Scopes während des Zustimmungsflows.

**Dokumentiere erforderliche Scopes in deiner README:**
```markdown
## Authentifizierung

Dieses Plugin erfordert folgende Asana-Berechtigungen:
- Aufgaben und Projekte lesen
- Aufgaben erstellen und aktualisieren
- Auf Workspace-Daten zugreifen
```

### Token-Speicherung

Token werden von Claude Code sicher gespeichert:
- Nicht für Plugins zugänglich
- Verschlüsselt im Ruhezustand
- Automatische Erneuerung
- Gelöscht bei Abmeldung

### OAuth-Fehlerbehebung

**Authentifizierungsschleife:**
- Zwischengespeicherte Token löschen (ab- und wieder anmelden)
- OAuth-Redirect-URLs prüfen
- Server-OAuth-Konfiguration prüfen

**Scope-Probleme:**
- Benutzer muss möglicherweise für neue Scopes erneut autorisieren
- Server-Dokumentation für erforderliche Scopes prüfen

**Token-Ablauf:**
- Claude Code erneuert automatisch
- Bei fehlgeschlagener Erneuerung wird erneute Authentifizierung angefordert

## Token-basierte Authentifizierung

### Bearer-Token

Am häufigsten für HTTP- und WebSocket-Server.

**Konfiguration:**
```json
{
  "api": {
    "type": "http",
    "url": "https://api.example.com/mcp",
    "headers": {
      "Authorization": "Bearer ${API_TOKEN}"
    }
  }
}
```

**Umgebungsvariable:**
```bash
export API_TOKEN="dein-geheimes-token-hier"
```

### API-Schlüssel

Alternative zu Bearer-Token, oft in benutzerdefinierten Headers.

**Konfiguration:**
```json
{
  "api": {
    "type": "http",
    "url": "https://api.example.com/mcp",
    "headers": {
      "X-API-Key": "${API_KEY}",
      "X-API-Secret": "${API_SECRET}"
    }
  }
}
```

### Benutzerdefinierte Header

Dienste können benutzerdefinierte Authentifizierungs-Header verwenden.

**Konfiguration:**
```json
{
  "service": {
    "type": "sse",
    "url": "https://mcp.example.com/sse",
    "headers": {
      "X-Auth-Token": "${AUTH_TOKEN}",
      "X-User-ID": "${USER_ID}",
      "X-Tenant-ID": "${TENANT_ID}"
    }
  }
}
```

### Token-Anforderungen dokumentieren

Immer in deiner README dokumentieren:

```markdown
## Einrichtung

### Erforderliche Umgebungsvariablen

Setze diese Umgebungsvariablen, bevor du das Plugin verwendest:

\`\`\`bash
export API_TOKEN="dein-token-hier"
export API_SECRET="dein-secret-hier"
\`\`\`

### Token erhalten

1. Besuche https://api.example.com/tokens
2. Erstelle ein neues API-Token
3. Kopiere Token und Secret
4. Setze Umgebungsvariablen wie oben gezeigt

### Token-Berechtigungen

Das API-Token benötigt folgende Berechtigungen:
- Lesezugriff auf Ressourcen
- Schreibzugriff zum Erstellen von Elementen
- Löschzugriff (optional, für Aufräumoperationen)
\`\`\`
```

## Umgebungsvariablen-Authentifizierung (stdio)

### Credentials an Server übergeben

Für stdio-Server, Credentials über Umgebungsvariablen übergeben:

```json
{
  "database": {
    "command": "python",
    "args": ["-m", "mcp_server_db"],
    "env": {
      "DATABASE_URL": "${DATABASE_URL}",
      "DB_USER": "${DB_USER}",
      "DB_PASSWORD": "${DB_PASSWORD}"
    }
  }
}
```

### Benutzer-Umgebungsvariablen

```bash
# Benutzer setzt diese in seiner Shell
export DATABASE_URL="postgresql://localhost/meinedb"
export DB_USER="meinbenutzer"
export DB_PASSWORD="meinpasswort"
```

### Dokumentationsvorlage

```markdown
## Datenbank-Konfiguration

Setze diese Umgebungsvariablen:

\`\`\`bash
export DATABASE_URL="postgresql://host:port/datenbank"
export DB_USER="benutzername"
export DB_PASSWORD="passwort"
\`\`\`

Oder erstelle eine `.env`-Datei (zur `.gitignore` hinzufügen):

\`\`\`
DATABASE_URL=postgresql://localhost:5432/meinedb
DB_USER=meinbenutzer
DB_PASSWORD=meinpasswort
\`\`\`

Laden mit: \`source .env\` oder \`export $(cat .env | xargs)\`
\`\`\`
```

## Dynamische Header

### Header-Hilfsskript

Für Token, die sich ändern oder ablaufen, verwende ein Hilfsskript:

```json
{
  "api": {
    "type": "sse",
    "url": "https://api.example.com",
    "headersHelper": "${CLAUDE_PLUGIN_ROOT}/scripts/get-headers.sh"
  }
}
```

**Skript (get-headers.sh):**
```bash
#!/bin/bash
# Dynamische Authentifizierungs-Header generieren

# Frisches Token abrufen
TOKEN=$(get-fresh-token-from-somewhere)

# JSON-Header ausgeben
cat <<EOF
{
  "Authorization": "Bearer $TOKEN",
  "X-Timestamp": "$(date -Iseconds)"
}
EOF
```

### Anwendungsfälle für dynamische Header

- Kurzlebige Token, die Erneuerung benötigen
- Token mit HMAC-Signaturen
- Zeitbasierte Authentifizierung
- Dynamische Mandanten-/Workspace-Auswahl

## Sicherheits-Best-Practices

### MACHEN

- **Umgebungsvariablen verwenden:**
```json
{
  "headers": {
    "Authorization": "Bearer ${API_TOKEN}"
  }
}
```

- **Erforderliche Variablen in README dokumentieren**

- **Immer HTTPS/WSS verwenden**

- **Token-Rotation implementieren**

- **Token sicher speichern (Env-Vars, nicht Dateien)**

- **OAuth die Authentifizierung überlassen, wenn verfügbar**

### NICHT MACHEN

- **Token fest codieren:**
```json
{
  "headers": {
    "Authorization": "Bearer sk-abc123..."  // NIEMALS!
  }
}
```

- **Token in Git committen**

- **Token in Dokumentation teilen**

- **HTTP statt HTTPS verwenden**

- **Token in Plugin-Dateien speichern**

- **Token oder sensible Header loggen**

## Multi-Tenancy-Muster

### Workspace-/Mandantenauswahl

**Über Umgebungsvariable:**
```json
{
  "api": {
    "type": "http",
    "url": "https://api.example.com/mcp",
    "headers": {
      "Authorization": "Bearer ${API_TOKEN}",
      "X-Workspace-ID": "${WORKSPACE_ID}"
    }
  }
}
```

**Über URL:**
```json
{
  "api": {
    "type": "http",
    "url": "https://${TENANT_ID}.api.example.com/mcp"
  }
}
```

### Benutzerspezifische Konfiguration

Benutzer setzen ihren eigenen Workspace:

```bash
export WORKSPACE_ID="mein-workspace-123"
export TENANT_ID="meine-firma"
```

## Authentifizierungs-Fehlerbehebung

### Häufige Probleme

**401 Unauthorized:**
- Prüfen, ob Token korrekt gesetzt ist
- Prüfen, ob Token abgelaufen ist
- Prüfen, ob Token erforderliche Berechtigungen hat
- Header-Format prüfen

**403 Forbidden:**
- Token gültig, aber fehlende Berechtigungen
- Scope/Berechtigungen prüfen
- Workspace-/Mandanten-ID prüfen
- Admin-Genehmigung erforderlich

**Token nicht gefunden:**
```bash
# Prüfen, ob Umgebungsvariable gesetzt ist
echo $API_TOKEN

# Wenn leer, setzen
export API_TOKEN="dein-token"
```

**Token im falschen Format:**
```json
// Korrekt
"Authorization": "Bearer sk-abc123"

// Falsch
"Authorization": "sk-abc123"
```

### Authentifizierung debuggen

**Debug-Modus aktivieren:**
```bash
claude --debug
```

Suche nach:
- Authentifizierungs-Header-Werte (bereinigt)
- OAuth-Flow-Fortschritt
- Token-Erneuerungsversuche
- Authentifizierungsfehler

**Authentifizierung separat testen:**
```bash
# HTTP-Endpunkt testen
curl -H "Authorization: Bearer $API_TOKEN" \
     https://api.example.com/mcp/health

# Sollte 200 OK zurückgeben
```

## Migrationsmuster

### Von fest codiert zu Umgebungsvariablen

**Vorher:**
```json
{
  "headers": {
    "Authorization": "Bearer sk-fest-codiertes-token"
  }
}
```

**Nachher:**
```json
{
  "headers": {
    "Authorization": "Bearer ${API_TOKEN}"
  }
}
```

**Migrationsschritte:**
1. Umgebungsvariable zur Plugin-README hinzufügen
2. Konfiguration auf ${VAR} aktualisieren
3. Mit gesetzter Variable testen
4. Fest codierten Wert entfernen
5. Änderungen committen

### Von Basic Auth zu OAuth

**Vorher:**
```json
{
  "headers": {
    "Authorization": "Basic ${BASE64_CREDENTIALS}"
  }
}
```

**Nachher:**
```json
{
  "type": "sse",
  "url": "https://mcp.example.com/sse"
}
```

**Vorteile:**
- Bessere Sicherheit
- Keine Credential-Verwaltung
- Automatische Token-Erneuerung
- Eingeschränkte Berechtigungen

## Fortgeschrittene Authentifizierung

### Mutual TLS (mTLS)

Einige Enterprise-Dienste erfordern Client-Zertifikate.

**Nicht direkt in MCP-Konfiguration unterstützt.**

**Workaround:** In stdio-Server wrappen, der mTLS behandelt:

```json
{
  "secure-api": {
    "command": "${CLAUDE_PLUGIN_ROOT}/servers/mtls-wrapper",
    "args": ["--cert", "${CLIENT_CERT}", "--key", "${CLIENT_KEY}"],
    "env": {
      "API_URL": "https://secure.example.com"
    }
  }
}
```

### JWT-Token

JWT-Token dynamisch mit Header-Hilfsskript generieren:

```bash
#!/bin/bash
# generate-jwt.sh

# JWT generieren (unter Verwendung einer Bibliothek oder API-Aufruf)
JWT=$(generate-jwt-token)

echo "{\"Authorization\": \"Bearer $JWT\"}"
```

```json
{
  "headersHelper": "${CLAUDE_PLUGIN_ROOT}/scripts/generate-jwt.sh"
}
```

### HMAC-Signaturen

Für APIs, die Request-Signing erfordern:

```bash
#!/bin/bash
# generate-hmac.sh

TIMESTAMP=$(date -Iseconds)
SIGNATURE=$(echo -n "$TIMESTAMP" | openssl dgst -sha256 -hmac "$SECRET_KEY" | cut -d' ' -f2)

cat <<EOF
{
  "X-Timestamp": "$TIMESTAMP",
  "X-Signature": "$SIGNATURE",
  "X-API-Key": "$API_KEY"
}
EOF
```

## Best-Practices-Zusammenfassung

### Für Plugin-Entwickler

1. **OAuth bevorzugen**, wenn der Dienst es unterstützt
2. **Umgebungsvariablen** für Token verwenden
3. **Alle erforderlichen Variablen** in README dokumentieren
4. **Einrichtungsanleitung** mit Beispielen bereitstellen
5. **Niemals Credentials committen**
6. **Nur HTTPS/WSS verwenden**
7. **Authentifizierung gründlich testen**

### Für Plugin-Benutzer

1. **Umgebungsvariablen setzen** vor Plugin-Nutzung
2. **Token sicher** und privat halten
3. **Token regelmäßig rotieren**
4. **Verschiedene Token** für Dev/Prod verwenden
5. **.env-Dateien nicht** in Git committen
6. **OAuth-Scopes prüfen** vor Autorisierung

## Fazit

Wähle die Authentifizierungsmethode, die den Anforderungen deines MCP-Servers entspricht:
- **OAuth** für Cloud-Dienste (am einfachsten für Benutzer)
- **Bearer-Token** für API-Dienste
- **Umgebungsvariablen** für stdio-Server
- **Dynamische Header** für komplexe Auth-Flows

Priorisiere immer Sicherheit und stelle klare Einrichtungsdokumentation für Benutzer bereit.
