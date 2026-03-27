# Plan

Erstelle einen detaillierten Implementierungsplan für Änderungen an diesem Workspace. Pläne sind gründliche Dokumente, die den vollständigen Kontext, die Begründung und schrittweise Aufgaben erfassen, um eine Änderung mit vollständiger Abstimmung im gesamten Projekt umzusetzen.

## Variablen

anforderung: $ARGUMENTS (beschreibe, was du planen möchtest — neuer Command, neuer Workflow, strukturelle Änderung, Template-Update, etc.)

---

## Anweisungen

- **WICHTIG:** Du erstellst einen PLAN, keine Implementierung. Recherchiere gründlich, denke sorgfältig nach, dann erstelle ein umfassendes Plan-Dokument.
- Nutze deine Reasoning-Fähigkeiten, um intensiv über die Anforderung, die Workspace-Struktur und den besten Ansatz nachzudenken.
- Recherchiere den Workspace, um bestehende Patterns, Konventionen und die Einordnung dieser Änderung zu verstehen.
- Erstelle den Plan im `plans/`-Verzeichnis mit Dateiname: `YYYY-MM-DD-{beschreibender-name}.md`
  - Verwende das heutige Datum
  - Ersetze `{beschreibender-name}` durch einen kurzen Namen in Kebab-Case (z.B. "gaeste-recherche-command-hinzufuegen", "outputs-umstrukturieren", "outreach-workflow-erstellen")
- Fülle jeden Abschnitt des Plan-Formats unten aus. Ersetze alle `<Platzhalter>` durch spezifische, umsetzbare Inhalte.
- Sei gründlich — dieser Plan wird von `/implement` ausgeführt und braucht genug Detail, um ohne Mehrdeutigkeit umgesetzt zu werden.
- Folge bestehenden Patterns. Studiere ähnliche Dateien im Workspace, bevor du neue Strukturen vorschlägst.

---

## Recherche-Phase

Bevor du den Plan schreibst, untersuche:

1. **Kern-Referenzdateien lesen:**
   - `CLAUDE.md` — Workspace-Überblick
   - `context/` — Hintergrund-Kontext über den User und das Projekt

2. **Relevante Bereiche erkunden:**
   - Bei Command-Erstellung: bestehende Commands in `.claude/commands/` lesen
   - Bei Output-Änderungen: `outputs/`-Struktur und Beispiele erkunden
   - Bei Template-Updates: `reference/` auf bestehende Patterns prüfen
   - Bei Skript-Erstellung: `scripts/` auf Konventionen prüfen

3. **Zusammenhänge verstehen:**
   - Wie hängt diese Änderung mit bestehenden Workflows zusammen?
   - Welche Dateien referenzieren oder hängen von geänderten Bereichen ab?
   - Gibt es Namenskonventionen zu befolgen?

---

## Plan-Format

Schreibe den Plan mit genau dieser Struktur:

```markdown
# Plan: <beschreibender Titel>

**Erstellt:** <YYYY-MM-DD>
**Status:** Entwurf
**Anforderung:** <einzeilige Zusammenfassung der Anforderung>

---

## Überblick

### Was dieser Plan erreicht

<2-3 Sätze, die das Endergebnis beschreiben und warum es wichtig ist>

### Warum das wichtig ist

<Verbinde diese Änderung mit den Zielen oder der Mission des Projekts. Wie schafft das Mehrwert?>

---

## Aktueller Zustand

### Relevante bestehende Struktur

<Liste der Dateien, Ordner oder Patterns, die existieren und mit dieser Änderung zusammenhängen>

### Lücken oder Probleme, die adressiert werden

<Was fehlt, ist defekt oder suboptimal, das dieser Plan behebt?>

---

## Vorgeschlagene Änderungen

### Zusammenfassung der Änderungen

<Aufzählung aller Änderungen auf hoher Ebene>

### Neue Dateien erstellen

<Liste jeder neuen Datei mit vollständigem Pfad und einzeiliger Beschreibung des Zwecks>

| Dateipfad         | Zweck                              |
| ----------------- | ---------------------------------- |
| `pfad/zur/datei.md` | Beschreibung der Dateifunktion    |

### Zu ändernde Dateien

<Liste jeder zu ändernden Datei und Zusammenfassung der Änderungen>

| Dateipfad         | Änderungen                         |
| ----------------- | ---------------------------------- |
| `pfad/zur/datei.md` | Beschreibung der Modifikationen  |

### Zu löschende Dateien (falls vorhanden)

<Liste aller zu entfernenden Dateien und Begründung>

---

## Design-Entscheidungen

### Getroffene Schlüsselentscheidungen

<Liste wichtiger Design-Entscheidungen und die Begründung dahinter>

1. **<Entscheidung>**: <Begründung>
2. **<Entscheidung>**: <Begründung>

### Betrachtete Alternativen

<Welche anderen Ansätze wurden erwogen und warum wurden sie verworfen?>

### Offene Fragen (falls vorhanden)

<Liste aller Entscheidungen, die User-Input vor der Implementierung benötigen>

---

## Schritt-für-Schritt-Aufgaben

Führe diese Aufgaben während der Implementierung in der angegebenen Reihenfolge aus.

### Schritt 1: <Aufgabentitel>

<Detaillierte Beschreibung, was zu tun ist>

**Aktionen:**

- <Spezifische Aktion>
- <Spezifische Aktion>

**Betroffene Dateien:**

- `pfad/zur/datei.md`

---

### Schritt 2: <Aufgabentitel>

<Detaillierte Beschreibung, was zu tun ist>

**Aktionen:**

- <Spezifische Aktion>
- <Spezifische Aktion>

**Betroffene Dateien:**

- `pfad/zur/datei.md`

---

<Fahre mit so vielen Schritten wie nötig fort. Sei gründlich. Beinhalte:>
<- Neue Dateien erstellen (mit vollständigen Inhaltsspezifikationen)>
<- Bestehende Dateien ändern (mit Vorher/Nachher oder spezifischen Edits)>
<- Querverweise aktualisieren>
<- Test-/Validierungsschritte>

---

## Verbindungen & Abhängigkeiten

### Dateien, die diesen Bereich referenzieren

<Liste aller Dateien, die auf geänderte Bereiche verlinken oder davon abhängen>

### Nötige Updates für Konsistenz

<Liste aller Dokumentationen, Referenzen oder verwandten Dateien, die aktualisiert werden müssen>

### Auswirkungen auf bestehende Workflows

<Beschreibe, wie sich dies auf bestehende Commands, Outputs oder Prozesse auswirkt>

---

## Validierungs-Checkliste

So überprüfst du, ob die Implementierung vollständig und korrekt ist:

- [ ] <Überprüfungsschritt — z.B. "Neuer Command läuft ohne Fehler">
- [ ] <Überprüfungsschritt — z.B. "Output-Dateien am richtigen Ort erstellt">
- [ ] <Überprüfungsschritt — z.B. "CLAUDE.md aktualisiert, um neue Struktur widerzuspiegeln">
- [ ] <Überprüfungsschritt — z.B. "Querverweise aktualisiert und gültig">

---

## Erfolgskriterien

Die Implementierung ist abgeschlossen, wenn:

1. <Spezifisches, messbares Kriterium>
2. <Spezifisches, messbares Kriterium>
3. <Spezifisches, messbares Kriterium>

---

## Notizen

<Zusätzlicher Kontext, zukünftige Überlegungen oder verwandte Ideen, die nützlich sein könnten>
```

---

## Qualitätsstandards

- **Vollständigkeit:** Jeder Abschnitt mit spezifischem Inhalt ausgefüllt, keine generischen Platzhalter übrig
- **Umsetzbarkeit:** Schritte detailliert genug, dass `/implement` sie ohne Rückfragen ausführen kann
- **Konsistenz:** Folgt bestehenden Workspace-Patterns und Namenskonventionen
- **Klarheit:** Jemand, der das Projekt nicht kennt, könnte den Plan verstehen und umsetzen
- **Nachvollziehbarkeit:** Änderungen sind mit Zielen und Begründungen verknüpft

---

## Bericht

Nach Erstellung des Plans:

1. Liefere eine kurze Zusammenfassung, was der Plan abdeckt
2. Liste alle offenen Fragen auf, die User-Input vor der Implementierung benötigen
3. Gib den vollständigen Pfad zur Plan-Datei an: `plans/YYYY-MM-DD-{name}.md`
4. Erinnere den User daran, `/implement plans/YYYY-MM-DD-{name}.md` zur Umsetzung auszuführen
