# MORIAH · Automatische Aktualisierung und Wiederherstellung

Die Nachrichten werden alle vier Stunden gesammelt. Ein unabhängiger GitHub-Workflow kontrolliert stündlich und nach jedem abgeschlossenen Veröffentlichungslauf die öffentliche Zeitung. Es wird die tatsächlich ausgelieferte Website geprüft, nicht nur der Datenstand im Repository.

## Wiederherstellung der Quellen

- Vorübergehende Verbindungsfehler, HTTP 429 und Serverfehler werden erneut versucht. `Retry-After` wird mit einer kurzen Obergrenze berücksichtigt. Dauerhafte 403/404-Antworten führen zur nächsten Quelle beziehungsweise Ersatzadresse.
- Jeder Publisher kann mehrere konfigurierte Feed-Adressen haben. Die zuletzt funktionierende Adresse wird in `data/feed-state.json` gespeichert und beim nächsten Mal zuerst geprüft.
- Nach einem Feed-Ausfall sucht das Programm auf der offiziellen Homepage und gegebenenfalls einer angegebenen RSS-Verzeichnisseite nach vom Publisher angebotenen Feeds. Nur HTTPS-Adressen auf erlaubten Publisher-Domains kommen infrage. Die Adresse wird erst nach erfolgreicher RSS-/Atom-Prüfung und vorhandenen datierten Meldungen als funktionierend verwendet.
- Die Suche ist auf eine kleine Zahl von Adressen, ein Zeitbudget je Quelle und höchstens einmal pro Tag begrenzt. Fachrubriken wie JPost Judaism und Culture haben zusätzliche Themenfilter für entdeckte Adressen.
- Ein erreichbarer Feed mit zu alten Meldungen wird als `stale` geführt. Er gilt nicht als frischer Nachrichtenstrom. Andere Publisher können den Nachrichtentisch weiter versorgen.
- Die Startseiten-Auswahl bevorzugt Meldungen aus den letzten 36 Stunden; innerhalb dieser Gruppe werden Originalmeldungen in der gewählten Sprache bevorzugt. Die ursprünglichen Publikationsdaten bleiben erhalten. Bei einem Totalausfall wird das Datum der letzten erfolgreichen Sammlung nicht durch einen neuen Versuch ersetzt. Nach zwölf Stunden ohne Aktualisierung oder bei einer als gestört erkannten Sammlung zeigt die Startseite einen Hinweis.

## Wiederherstellung der Veröffentlichung

`scripts/watchdog.py` verwendet ausschließlich den eingebauten Repository-Token mit Actions-Schreibrecht. Es ist kein zusätzlicher persönlicher Token erforderlich.

Der Wächter prüft:

1. Läuft bereits eine Veröffentlichung? Dann wird keine zweite gestartet.
2. Ist ein Lauf länger als 45 Minuten hängen geblieben? Dann wird er beendet.
3. Ist die öffentliche Sammlung älter als acht Stunden, fehlen Nachrichten aus den letzten 36 Stunden, meldet die Quellenprüfung eine Störung oder ist der letzte Veröffentlichungslauf fehlgeschlagen? Dann startet ein neuer Lauf vom aktuellen Stand von `main`.
4. Wurden bereits drei Wiederherstellungsläufe innerhalb von sechs Stunden gestartet? Dann wird die zusätzliche Wiederholung begrenzt. Die regulären Vier-Stunden-Läufe bleiben aktiv. Dadurch entsteht keine unbeschränkte Fehlerschleife.

Auch ein erneuter Versuch eines GitHub-Laufs nutzt automatisch den Wiederherstellungsmodus. Ein Wiederherstellungslauf nutzt vorhandene Übersetzungen und gespeicherte Studiendaten. Nachrichtenfeeds werden weiterhin live gesammelt und geprüft. Der normale Lauf versucht anschließend wieder die vollständige Übersetzung und Aktualisierung aller Studienbereiche.

Das Pages-Paket trägt eine eindeutige Kennung aus Laufnummer und Versuch. Dadurch können direkte Wiederholungen nicht mit alten Paketen desselben GitHub-Laufs verwechselt werden.

Ein Publikationsmarker in `data/publication.json` benennt den konkreten GitHub-Lauf und dessen Versuch. Nach dem Deployment prüft das Programm über die öffentliche Website, ob Marker und Nachrichtendaten übereinstimmen. Ein übersprungener oder fehlgeschlagener Pages-Deploy wird nicht als erfolgreiche Veröffentlichung behandelt.

## Bewegliche Studienkalender und Prüfungen

Rollende externe Kalender können vergangene Termine entfernen. Bekannte Einträge werden deshalb begrenzt zusammengeführt. Fehlt ein Wochenabschnitt in der externen Datei, berechnet der lokal gebündelte Hebcal-Kalender die Lesung. Veröffentlichtes Studienmaterial wird nur verlinkt, wenn der passende Katalogeintrag vorhanden ist.

Leere oder unvollständige optionale Q&A-/Studienkataloge ersetzen keinen funktionierenden gespeicherten Bereich. Diese optionalen Daten dürfen den Nachrichtentisch nicht durch eine vorübergehende Netzstörung blockieren. Die Prüfungen verwenden für feste historische Erwartungen feste Beispieldaten; veränderliche Kataloge werden auf ihre Struktur und funktionale Regeln geprüft.

Die Wiederherstellung umgeht keine Zugangssperren und verändert keinen Programmcode auf Verdacht. Unbekannte echte Programmfehler können weiterhin eine Korrektur erfordern. Solche Fehler bleiben in GitHub Actions und auf der Statusseite nachvollziehbar. Vorhandene Prüfungen werden bei der Wiederherstellung nicht abgeschaltet.

## Sichtbare Kontrolle

- Öffentliche Statusseite: https://moriahise.github.io/Moriah/status.html
- Hauptlauf: `.github/workflows/newspaper.yml`
- Wächter: `.github/workflows/watchdog.yml`
- Feed-Versuche, letzte Erfolge und verwendete Ersatzadressen: `data/health.json` und `data/feed-state.json`
- Optionale Studienbereiche mit Zustand `ok`/`cached`: `data/ecosystem.json`

Lokal: `npm run build:integrations`, `npm test`, `python -m unittest discover -s tests -v`, `python scripts/pipeline.py --no-translate`, `python scripts/ecosystem.py`, `python scripts/publication.py prepare`, `python scripts/build.py`, `python scripts/verify_build.py`.
