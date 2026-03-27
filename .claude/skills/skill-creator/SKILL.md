---
name: skill-creator
description: Skills erstellen oder aktualisieren. Verwenden beim Entwerfen, Strukturieren oder Paketieren von Skills mit Skripten, Referenzen und Assets.
---

# Skill Creator

Dieser Skill bietet Anleitung zum Erstellen effektiver Skills.

## Über Skills

Skills sind modulare, eigenständige Pakete, die die Fähigkeiten von Codex erweitern, indem sie spezialisiertes Wissen, Workflows und Tools bereitstellen. Man kann sie sich als "Onboarding-Guides" für bestimmte Domänen oder Aufgaben vorstellen — sie verwandeln Codex von einem Allzweck-Agenten in einen spezialisierten Agenten, der mit prozeduralem Wissen ausgestattet ist, das kein Modell vollständig besitzen kann.

### Was Skills bereitstellen

1. Spezialisierte Workflows - Mehrstufige Prozeduren für bestimmte Domänen
2. Tool-Integrationen - Anweisungen für die Arbeit mit bestimmten Dateiformaten oder APIs
3. Domänenexpertise - Unternehmensspezifisches Wissen, Schemas, Geschäftslogik
4. Gebündelte Ressourcen - Skripte, Referenzen und Assets für komplexe und wiederkehrende Aufgaben

## Kernprinzipien

### Kürze ist entscheidend

Das Kontextfenster ist ein öffentliches Gut. Skills teilen sich das Kontextfenster mit allem anderen, was Codex braucht: System-Prompt, Gesprächsverlauf, Metadaten anderer Skills und die eigentliche Benutzeranfrage.

**Standardannahme: Codex ist bereits sehr intelligent.** Füge nur Kontext hinzu, den Codex nicht bereits hat. Hinterfrage jede Information: "Braucht Codex diese Erklärung wirklich?" und "Rechtfertigt dieser Absatz seine Token-Kosten?"

Bevorzuge knappe Beispiele gegenüber ausschweifenden Erklärungen.

### Angemessene Freiheitsgrade setzen

Passe den Spezifitätsgrad an die Fragilität und Variabilität der Aufgabe an:

**Hohe Freiheit (textbasierte Anweisungen)**: Verwenden, wenn mehrere Ansätze gültig sind, Entscheidungen vom Kontext abhängen oder Heuristiken den Ansatz leiten.

**Mittlere Freiheit (Pseudocode oder Skripte mit Parametern)**: Verwenden, wenn ein bevorzugtes Pattern existiert, gewisse Variation akzeptabel ist oder Konfiguration das Verhalten beeinflusst.

**Niedrige Freiheit (spezifische Skripte, wenige Parameter)**: Verwenden, wenn Operationen fragil und fehleranfällig sind, Konsistenz kritisch ist oder eine bestimmte Reihenfolge eingehalten werden muss.

Stelle dir Codex vor, der einen Pfad erkundet: eine schmale Brücke mit Klippen braucht spezifische Leitplanken (niedrige Freiheit), während ein offenes Feld viele Routen erlaubt (hohe Freiheit).

### Anatomie eines Skills

Jeder Skill besteht aus einer erforderlichen SKILL.md-Datei und optionalen gebündelten Ressourcen:

```
skill-name/
├── SKILL.md (erforderlich)
│   ├── YAML-Frontmatter-Metadaten (erforderlich)
│   │   ├── name: (erforderlich)
│   │   └── description: (erforderlich)
│   └── Markdown-Anweisungen (erforderlich)
└── Gebündelte Ressourcen (optional)
    ├── scripts/          - Ausführbarer Code (Python/Bash/etc.)
    ├── references/       - Dokumentation, die bei Bedarf in den Kontext geladen wird
    └── assets/           - Dateien, die in der Ausgabe verwendet werden (Vorlagen, Icons, Fonts, etc.)
```

#### SKILL.md (erforderlich)

Jede SKILL.md besteht aus:

- **Frontmatter** (YAML): Enthält `name`- und `description`-Felder. Dies sind die einzigen Felder, die Codex liest, um zu bestimmen, wann der Skill verwendet wird. Daher ist es sehr wichtig, klar und umfassend zu beschreiben, was der Skill ist und wann er verwendet werden soll.
- **Body** (Markdown): Anweisungen und Anleitungen zur Nutzung des Skills. Werden erst NACH dem Auslösen des Skills geladen (falls überhaupt).

#### Gebündelte Ressourcen (optional)

##### Skripte (`scripts/`)

Ausführbarer Code (Python/Bash/etc.) für Aufgaben, die deterministische Zuverlässigkeit erfordern oder wiederholt neu geschrieben werden.

- **Wann einschließen**: Wenn derselbe Code wiederholt neu geschrieben wird oder deterministische Zuverlässigkeit benötigt wird
- **Beispiel**: `scripts/rotate_pdf.py` für PDF-Rotationsaufgaben
- **Vorteile**: Token-effizient, deterministisch, kann ohne Laden in den Kontext ausgeführt werden
- **Hinweis**: Skripte müssen möglicherweise trotzdem von Codex gelesen werden für Patching oder umgebungsspezifische Anpassungen

##### Referenzen (`references/`)

Dokumentation und Referenzmaterial, das bei Bedarf in den Kontext geladen wird, um Codex' Prozess und Denken zu informieren.

- **Wann einschließen**: Für Dokumentation, die Codex während der Arbeit referenzieren sollte
- **Beispiele**: `references/finance.md` für Finanz-Schemas, `references/mnda.md` für Unternehmens-NDA-Vorlage, `references/policies.md` für Unternehmensrichtlinien, `references/api_docs.md` für API-Spezifikationen
- **Anwendungsfälle**: Datenbankschemas, API-Dokumentation, Domänenwissen, Unternehmensrichtlinien, detaillierte Workflow-Guides
- **Vorteile**: Hält SKILL.md schlank, wird nur geladen wenn Codex es für nötig hält
- **Best Practice**: Bei großen Dateien (>10k Wörter) grep-Suchmuster in SKILL.md aufnehmen
- **Duplikate vermeiden**: Informationen sollten entweder in SKILL.md oder in Referenzdateien stehen, nicht in beiden. Bevorzuge Referenzdateien für detaillierte Informationen, es sei denn, sie sind wirklich kernrelevant für den Skill — so bleibt SKILL.md schlank und Informationen auffindbar, ohne das Kontextfenster zu belasten. Nur wesentliche prozedurale Anweisungen und Workflow-Anleitungen in SKILL.md behalten; detailliertes Referenzmaterial, Schemas und Beispiele in Referenzdateien verschieben.

##### Assets (`assets/`)

Dateien, die nicht in den Kontext geladen werden sollen, sondern in der Ausgabe von Codex verwendet werden.

- **Wann einschließen**: Wenn der Skill Dateien benötigt, die in der endgültigen Ausgabe verwendet werden
- **Beispiele**: `assets/logo.png` für Marken-Assets, `assets/slides.pptx` für PowerPoint-Vorlagen, `assets/frontend-template/` für HTML/React-Boilerplate, `assets/font.ttf` für Typografie
- **Anwendungsfälle**: Vorlagen, Bilder, Icons, Boilerplate-Code, Fonts, Beispieldokumente, die kopiert oder modifiziert werden
- **Vorteile**: Trennt Ausgabe-Ressourcen von Dokumentation, ermöglicht Codex Dateien zu verwenden ohne sie in den Kontext zu laden

#### Was NICHT in einen Skill gehört

Ein Skill sollte nur wesentliche Dateien enthalten, die seine Funktionalität direkt unterstützen. Erstelle KEINE überflüssigen Dokumentations- oder Hilfsdateien, einschließlich:

- README.md
- INSTALLATION_GUIDE.md
- QUICK_REFERENCE.md
- CHANGELOG.md
- etc.

Der Skill sollte nur die Informationen enthalten, die ein KI-Agent benötigt, um die Aufgabe zu erledigen. Er sollte keinen zusätzlichen Kontext über den Erstellungsprozess, Einrichtungs- und Testverfahren, benutzerseitige Dokumentation usw. enthalten. Zusätzliche Dokumentationsdateien erzeugen nur Ballast und Verwirrung.

### Progressive-Disclosure-Designprinzip

Skills verwenden ein dreistufiges Ladesystem für effizientes Kontext-Management:

1. **Metadaten (Name + Beschreibung)** - Immer im Kontext (~100 Wörter)
2. **SKILL.md Body** - Wenn der Skill ausgelöst wird (<5k Wörter)
3. **Gebündelte Ressourcen** - Nach Bedarf von Codex (unbegrenzt, da Skripte ohne Laden in den Kontext ausgeführt werden können)

#### Progressive-Disclosure-Muster

SKILL.md Body auf das Wesentliche beschränken und unter 500 Zeilen halten, um Kontext-Aufblähung zu minimieren. Inhalte in separate Dateien aufteilen, wenn diese Grenze erreicht wird. Beim Auslagern von Inhalten ist es sehr wichtig, sie aus SKILL.md zu referenzieren und klar zu beschreiben, wann sie gelesen werden sollen, damit der Leser des Skills weiß, dass sie existieren und wann er sie nutzen soll.

**Kernprinzip:** Wenn ein Skill mehrere Varianten, Frameworks oder Optionen unterstützt, nur den Kern-Workflow und die Auswahlhilfe in SKILL.md behalten. Variantenspezifische Details (Muster, Beispiele, Konfiguration) in separate Referenzdateien verschieben.

**Muster 1: High-Level-Guide mit Referenzen**

```markdown
# PDF-Verarbeitung

## Schnellstart

Text mit pdfplumber extrahieren:
[Code-Beispiel]

## Erweiterte Funktionen

- **Formularausfüllung**: Siehe [FORMS.md](FORMS.md) für vollständigen Guide
- **API-Referenz**: Siehe [REFERENCE.md](REFERENCE.md) für alle Methoden
- **Beispiele**: Siehe [EXAMPLES.md](EXAMPLES.md) für häufige Muster
```

Codex lädt FORMS.md, REFERENCE.md oder EXAMPLES.md nur bei Bedarf.

**Muster 2: Domänenspezifische Organisation**

Für Skills mit mehreren Domänen Inhalte nach Domäne organisieren, um das Laden irrelevanten Kontexts zu vermeiden:

```
bigquery-skill/
├── SKILL.md (Überblick und Navigation)
└── reference/
    ├── finance.md (Umsatz, Abrechnungsmetriken)
    ├── sales.md (Opportunities, Pipeline)
    ├── product.md (API-Nutzung, Features)
    └── marketing.md (Kampagnen, Attribution)
```

Wenn ein Benutzer nach Vertriebsmetriken fragt, liest Codex nur sales.md.

Ebenso für Skills, die mehrere Frameworks oder Varianten unterstützen, nach Variante organisieren:

```
cloud-deploy/
├── SKILL.md (Workflow + Anbieterauswahl)
└── references/
    ├── aws.md (AWS-Deployment-Muster)
    ├── gcp.md (GCP-Deployment-Muster)
    └── azure.md (Azure-Deployment-Muster)
```

Wenn der Benutzer AWS wählt, liest Codex nur aws.md.

**Muster 3: Bedingte Details**

Grundlegenden Inhalt zeigen, erweiterten Inhalt verlinken:

```markdown
# DOCX-Verarbeitung

## Dokumente erstellen

docx-js für neue Dokumente verwenden. Siehe [DOCX-JS.md](DOCX-JS.md).

## Dokumente bearbeiten

Für einfache Bearbeitungen das XML direkt modifizieren.

**Für Änderungsverfolgung**: Siehe [REDLINING.md](REDLINING.md)
**Für OOXML-Details**: Siehe [OOXML.md](OOXML.md)
```

Codex liest REDLINING.md oder OOXML.md nur, wenn der Benutzer diese Funktionen benötigt.

**Wichtige Richtlinien:**

- **Tief verschachtelte Referenzen vermeiden** - Referenzen eine Ebene tief von SKILL.md halten. Alle Referenzdateien sollten direkt aus SKILL.md verlinkt sein.
- **Längere Referenzdateien strukturieren** - Für Dateien länger als 100 Zeilen ein Inhaltsverzeichnis am Anfang aufnehmen, damit Codex den vollen Umfang bei der Vorschau sehen kann.

## Skill-Erstellungsprozess

Die Skill-Erstellung umfasst folgende Schritte:

1. Skill mit konkreten Beispielen verstehen
2. Wiederverwendbare Skill-Inhalte planen (Skripte, Referenzen, Assets)
3. Skill initialisieren (init_skill.py ausführen)
4. Skill bearbeiten (Ressourcen implementieren und SKILL.md schreiben)
5. Skill paketieren (package_skill.py ausführen)
6. Basierend auf realer Nutzung iterieren

Folge diesen Schritten in der angegebenen Reihenfolge. Überspringe nur, wenn es einen klaren Grund gibt, warum sie nicht anwendbar sind.

### Skill-Benennung

- Nur Kleinbuchstaben, Ziffern und Bindestriche verwenden; vom Benutzer bereitgestellte Titel in Kebab-Case normalisieren (z.B. "Plan Mode" -> `plan-mode`).
- Bei der Namensgenerierung einen Namen unter 64 Zeichen generieren (Buchstaben, Ziffern, Bindestriche).
- Kurze, verbgeführte Phrasen bevorzugen, die die Aktion beschreiben.
- Bei Tool-Namensraum verwenden, wenn es Klarheit oder Auslösung verbessert (z.B. `gh-address-comments`, `linear-address-issue`).
- Den Skill-Ordner genau nach dem Skill-Namen benennen.

### Schritt 1: Skill mit konkreten Beispielen verstehen

Diesen Schritt nur überspringen, wenn die Nutzungsmuster des Skills bereits klar verstanden sind. Er bleibt auch bei der Arbeit mit einem bestehenden Skill wertvoll.

Um einen effektiven Skill zu erstellen, müssen konkrete Beispiele für die Nutzung klar verstanden werden. Dieses Verständnis kann aus direkten Benutzerbeispielen oder aus generierten Beispielen stammen, die mit Benutzerfeedback validiert werden.

Zum Beispiel, beim Bau eines Bildbearbeitungs-Skills sind relevante Fragen:

- "Welche Funktionalität soll der Bildbearbeitungs-Skill unterstützen? Bearbeiten, Drehen, etwas anderes?"
- "Kannst du Beispiele geben, wie dieser Skill verwendet wird?"
- "Ich kann mir vorstellen, dass Benutzer Dinge sagen wie 'Entferne rote Augen aus diesem Bild' oder 'Drehe dieses Bild'. Gibt es andere Wege, wie du dir die Nutzung vorstellst?"
- "Was würde ein Benutzer sagen, das diesen Skill auslösen sollte?"

Um Benutzer nicht zu überfordern, vermeide zu viele Fragen in einer einzelnen Nachricht. Beginne mit den wichtigsten Fragen und stelle Folgefragen nach Bedarf.

Diesen Schritt abschließen, wenn ein klares Verständnis der Funktionalität besteht, die der Skill unterstützen soll.

### Schritt 2: Wiederverwendbare Skill-Inhalte planen

Um konkrete Beispiele in einen effektiven Skill umzuwandeln, analysiere jedes Beispiel indem du:

1. Überlegst, wie das Beispiel von Grund auf ausgeführt werden würde
2. Identifizierst, welche Skripte, Referenzen und Assets beim wiederholten Ausführen dieser Workflows hilfreich wären

Beispiel: Beim Bau eines `pdf-editor`-Skills für Anfragen wie "Hilf mir, dieses PDF zu drehen" zeigt die Analyse:

1. Das Drehen eines PDFs erfordert jedes Mal das Neuschreiben desselben Codes
2. Ein `scripts/rotate_pdf.py`-Skript wäre hilfreich im Skill zu speichern

Beispiel: Beim Design eines `frontend-webapp-builder`-Skills für Anfragen wie "Baue mir eine Todo-App" oder "Baue mir ein Dashboard zum Tracken meiner Schritte" zeigt die Analyse:

1. Das Schreiben einer Frontend-Webapp erfordert jedes Mal dasselbe HTML/React-Boilerplate
2. Eine `assets/hello-world/`-Vorlage mit den Boilerplate-HTML/React-Projektdateien wäre hilfreich im Skill zu speichern

Beispiel: Beim Bau eines `big-query`-Skills für Anfragen wie "Wie viele Benutzer haben sich heute eingeloggt?" zeigt die Analyse:

1. BigQuery abzufragen erfordert jedes Mal das Wiederentdecken der Tabellenschemas und -beziehungen
2. Eine `references/schema.md`-Datei, die die Tabellenschemas dokumentiert, wäre hilfreich im Skill zu speichern

Um die Skill-Inhalte festzulegen, analysiere jedes konkrete Beispiel, um eine Liste der wiederverwendbaren Ressourcen zu erstellen: Skripte, Referenzen und Assets.

### Schritt 3: Skill initialisieren

An diesem Punkt ist es Zeit, den Skill tatsächlich zu erstellen.

Diesen Schritt nur überspringen, wenn der zu entwickelnde Skill bereits existiert und Iteration oder Paketierung benötigt wird. In diesem Fall mit dem nächsten Schritt fortfahren.

Beim Erstellen eines neuen Skills von Grund auf immer das `init_skill.py`-Skript ausführen. Das Skript generiert bequem ein neues Skill-Vorlagenverzeichnis, das automatisch alles enthält, was ein Skill benötigt, und macht den Skill-Erstellungsprozess wesentlich effizienter und zuverlässiger.

Verwendung:

```bash
scripts/init_skill.py <skill-name> --path <ausgabe-verzeichnis> [--resources scripts,references,assets] [--examples]
```

Beispiele:

```bash
scripts/init_skill.py mein-skill --path skills/public
scripts/init_skill.py mein-skill --path skills/public --resources scripts,references
scripts/init_skill.py mein-skill --path skills/public --resources scripts --examples
```

Das Skript:

- Erstellt das Skill-Verzeichnis am angegebenen Pfad
- Generiert eine SKILL.md-Vorlage mit korrektem Frontmatter und TODO-Platzhaltern
- Erstellt optional Ressourcenverzeichnisse basierend auf `--resources`
- Fügt optional Beispieldateien hinzu, wenn `--examples` gesetzt ist

Nach der Initialisierung SKILL.md anpassen und Ressourcen nach Bedarf hinzufügen. Bei Verwendung von `--examples` Platzhalterdateien ersetzen oder löschen.

### Schritt 4: Skill bearbeiten

Beim Bearbeiten des (neu generierten oder bestehenden) Skills beachte, dass der Skill für eine andere Codex-Instanz erstellt wird. Füge Informationen hinzu, die für Codex nützlich und nicht offensichtlich wären. Überlege, welches prozedurale Wissen, welche domänenspezifischen Details oder welche wiederverwendbaren Assets einer anderen Codex-Instanz helfen würden, diese Aufgaben effektiver auszuführen.

#### Bewährte Design-Patterns lernen

Konsultiere diese hilfreichen Guides basierend auf den Anforderungen deines Skills:

- **Mehrstufige Prozesse**: Siehe references/workflows.md für sequenzielle Workflows und bedingte Logik
- **Spezifische Ausgabeformate oder Qualitätsstandards**: Siehe references/output-patterns.md für Vorlagen- und Beispielmuster

Diese Dateien enthalten bewährte Best Practices für effektives Skill-Design.

#### Mit wiederverwendbaren Skill-Inhalten beginnen

Um mit der Implementierung zu beginnen, starte mit den oben identifizierten wiederverwendbaren Ressourcen: `scripts/`-, `references/`- und `assets/`-Dateien. Beachte, dass dieser Schritt Benutzereingaben erfordern kann. Zum Beispiel muss der Benutzer beim Implementieren eines `brand-guidelines`-Skills möglicherweise Marken-Assets oder Vorlagen bereitstellen, die in `assets/` gespeichert werden, oder Dokumentation, die in `references/` gespeichert wird.

Hinzugefügte Skripte müssen durch tatsächliches Ausführen getestet werden, um sicherzustellen, dass keine Bugs vorhanden sind und die Ausgabe den Erwartungen entspricht. Bei vielen ähnlichen Skripten muss nur eine repräsentative Stichprobe getestet werden, um Vertrauen zu schaffen, dass alle funktionieren, während die Zeit bis zur Fertigstellung ausbalanciert wird.

Bei Verwendung von `--examples` alle Platzhalterdateien löschen, die für den Skill nicht benötigt werden. Nur Ressourcenverzeichnisse erstellen, die tatsächlich benötigt werden.

#### SKILL.md aktualisieren

**Schreibrichtlinien:** Immer Imperativ/Infinitivform verwenden.

##### Frontmatter

YAML-Frontmatter mit `name` und `description` schreiben:

- `name`: Der Skill-Name
- `description`: Dies ist der primäre Auslösemechanismus für deinen Skill und hilft Codex zu verstehen, wann der Skill verwendet werden soll.
  - Sowohl was der Skill tut als auch spezifische Auslöser/Kontexte für die Verwendung einschließen.
  - Alle "Wann verwenden"-Informationen hierhin — nicht in den Body. Der Body wird erst nach dem Auslösen geladen, daher sind "Wann diesen Skill verwenden"-Abschnitte im Body für Codex nicht hilfreich.
  - Beispielbeschreibung für einen `docx`-Skill: "Umfassende Dokumentenerstellung, -bearbeitung und -analyse mit Unterstützung für Änderungsverfolgung, Kommentare, Formatierungserhaltung und Textextraktion. Verwenden, wenn Codex mit professionellen Dokumenten (.docx-Dateien) arbeiten muss für: (1) Neue Dokumente erstellen, (2) Inhalte ändern oder bearbeiten, (3) Mit Änderungsverfolgung arbeiten, (4) Kommentare hinzufügen, oder andere Dokumentenaufgaben"

Keine anderen Felder in YAML-Frontmatter aufnehmen.

##### Body

Anweisungen zur Nutzung des Skills und seiner gebündelten Ressourcen schreiben.

### Schritt 5: Skill paketieren

Sobald die Entwicklung des Skills abgeschlossen ist, muss er in eine verteilbare .skill-Datei paketiert werden, die mit dem Benutzer geteilt wird. Der Paketierungsprozess validiert den Skill automatisch zuerst, um sicherzustellen, dass alle Anforderungen erfüllt sind:

```bash
scripts/package_skill.py <pfad/zum/skill-ordner>
```

Optionale Angabe des Ausgabeverzeichnisses:

```bash
scripts/package_skill.py <pfad/zum/skill-ordner> ./dist
```

Das Paketierungsskript wird:

1. **Validieren** — den Skill automatisch prüfen:
   - YAML-Frontmatter-Format und erforderliche Felder
   - Skill-Namenskonventionen und Verzeichnisstruktur
   - Beschreibungsvollständigkeit und -qualität
   - Dateiorganisation und Ressourcenreferenzen

2. **Paketieren** — den Skill, wenn die Validierung besteht, in eine .skill-Datei erstellen, die nach dem Skill benannt ist (z.B. `mein-skill.skill`) und alle Dateien enthält und die korrekte Verzeichnisstruktur für die Distribution beibehält. Die .skill-Datei ist eine ZIP-Datei mit .skill-Erweiterung.

Wenn die Validierung fehlschlägt, werden die Fehler gemeldet und ohne Paket-Erstellung beendet. Validierungsfehler beheben und den Paketierungsbefehl erneut ausführen.

### Schritt 6: Iterieren

Nach dem Testen des Skills können Benutzer Verbesserungen anfordern. Dies geschieht oft direkt nach der Nutzung des Skills, mit frischem Kontext darüber, wie der Skill performt hat.

**Iterations-Workflow:**

1. Skill an realen Aufgaben verwenden
2. Schwierigkeiten oder Ineffizienzen bemerken
3. Identifizieren, wie SKILL.md oder gebündelte Ressourcen aktualisiert werden sollten
4. Änderungen implementieren und erneut testen
