# Implementieren

Führe einen mit `/create-plan` erstellten Implementierungsplan aus. Lies den Plan gründlich, führe jeden Schritt der Reihe nach aus und berichte über die erledigte Arbeit.

## Variablen

plan_pfad: $ARGUMENTS (Pfad zur Plan-Datei, z.B. `plans/2026-01-28-gaeste-recherche-command.md`)

---

## Anweisungen

### Phase 1: Plan verstehen

1. **Lies die Plan-Datei vollständig.** Nicht überfliegen — jeden Abschnitt verstehen.
2. **Voraussetzungen prüfen:**
   - Gibt es offene Fragen, die vor dem Fortfahren beantwortet werden müssen?
   - Gibt es Abhängigkeiten von externen Ressourcen oder User-Entscheidungen?
   - Falls Blocker existieren, stoppen und den User fragen, bevor fortgefahren wird.
3. **Bestätigen, dass der Plan bereit ist:**
   - Status sollte "Entwurf" oder "Bereit" sein
   - Alle Abschnitte sollten ausgefüllt sein (kein Platzhalter-Text mehr)

---

### Phase 2: Plan ausführen

1. **Folge den Schritt-für-Schritt-Aufgaben in exakter Reihenfolge.**
   - Jeden Schritt vollständig abschließen, bevor zum nächsten übergegangen wird
   - Falls ein Schritt die Erstellung einer Datei beinhaltet, die vollständige Datei schreiben — keinen Stub
   - Falls ein Schritt die Änderung einer Datei beinhaltet, die Datei zuerst lesen, dann Änderungen präzise anwenden

2. **Für jede Aufgabe:**
   - Alle betroffenen Dateien lesen
   - Die spezifizierten Änderungen vornehmen
   - Überprüfen, ob die Änderung korrekt ist, bevor fortgefahren wird

3. **Probleme elegant behandeln:**
   - Falls ein Schritt nicht wie beschrieben ausgeführt werden kann, das Problem notieren und anpassen, wenn die Absicht klar ist
   - Bei Unsicherheit den User fragen, anstatt zu raten
   - Abweichungen vom Plan dokumentieren

---

### Phase 3: Validieren

1. **Die Validierungs-Checkliste** aus dem Plan durchgehen
   - Jeden Punkt abhaken
   - Fehlschläge notieren

2. **Erfolgskriterien überprüfen**
   - Bestätigen, dass jedes Kriterium erfüllt ist
   - Lücken notieren

3. **Querverweise und Konsistenz prüfen:**
   - Sicherstellen, dass neue Dateien dort referenziert werden, wo sie sollten
   - Prüfen, ob CLAUDE.md aktualisiert wurde, falls sich die Workspace-Struktur geändert hat
   - Bestätigen, dass Namenskonventionen eingehalten werden

---

### Phase 4: Plan-Status aktualisieren

Nach der Implementierung die Plan-Datei aktualisieren:

1. `**Status:** Entwurf` zu `**Status:** Implementiert` ändern
2. Einen Abschnitt "Implementierungsnotizen" am Ende hinzufügen:

```markdown
---

## Implementierungsnotizen

**Implementiert:** <YYYY-MM-DD>

### Zusammenfassung

<Kurze Zusammenfassung, was getan wurde>

### Abweichungen vom Plan

<Liste aller Änderungen während der Implementierung, oder "Keine">

### Aufgetretene Probleme

<Liste aller Probleme und wie sie gelöst wurden, oder "Keine">
```

---

## Qualitätsstandards

- **Gründlichkeit:** Jeder Schritt im Plan wird ausgeführt, nicht übersprungen
- **Präzision:** Änderungen entsprechen dem, was der Plan spezifiziert
- **Vollständigkeit:** Dateien werden vollständig geschrieben, nicht als Stubs
- **Konsistenz:** Alle Querverweise und Dokumentation aktualisiert
- **Nachvollziehbarkeit:** Abweichungen werden dokumentiert

---

## Bericht

Nach der Implementierung liefere:

1. **Zusammenfassung:** Aufzählung der erledigten Arbeit
2. **Geänderte Dateien:** Liste aller erstellten, geänderten oder gelöschten Dateien
3. **Validierungsergebnisse:** Status jedes Checklisten-Punkts
4. **Abweichungen:** Alle Änderungen vom ursprünglichen Plan
5. **Nächste Schritte:** Eventuelle Folgeaktionen (falls zutreffend)

Format:

```
## Implementierung abgeschlossen

### Zusammenfassung
- <Was wurde erledigt>
- <Was wurde erledigt>

### Geänderte Dateien
**Erstellt:**
- `pfad/zur/neuen-datei.md`

**Geändert:**
- `pfad/zur/geaenderten-datei.md`

**Gelöscht:**
- (keine)

### Validierung
- [x] <Bestandener Check>
- [x] <Bestandener Check>

### Abweichungen vom Plan
<Keine, oder Abweichungen auflisten>

### Plan-Status
`plans/YYYY-MM-DD-{name}.md` Status auf "Implementiert" aktualisiert
```
