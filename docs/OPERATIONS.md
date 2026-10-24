# MORIAH Betrieb und Wartung

## Normalbetrieb

Die öffentliche Zeitung sammelt alle vier Stunden. Der private Bereich erstellt zweimal täglich einen eigenen Vorschau-/Prüflauf. Die Wochenedition wird nach Mittwoch 18:00 Uhr Israel-Zeit angelegt. Sommer-/Winterzeit folgt `Asia/Jerusalem`; die UTC-Cronzeit ist nur ein Polling-Takt. Beim nächsten Lauf nach einem verpassten Termin wird die fällige Ausgabe nachgeholt und mit dem tatsächlichen Erstellungsdatum versehen.

Der erste Lauf erzeugt eine als Eröffnung gekennzeichnete Ausgabe. Eine einmal angelegte Ausgaben-JSON bleibt unverändert. Die laufende Website darf anschließend neue Nachrichten zeigen. Jede Wochenedition enthält Quellenverweise, Kalenderdaten, zehn Beiträge aus der 24-teiligen zweisprachigen Bibliothek und die Erklärung ihrer automatischen Herstellung. Die Bibliotheksbeiträge rotieren, ohne ihre Wiederverwendung als neue Recherche auszugeben.

## Prüfgates

1. HTTPS-Links, erlaubte Quellendomains, beschränkte Antwortgröße und XML ohne DTD/Entities.
2. Erkennbare Datumsangaben, keine weit in der Zukunft liegenden Meldungen, 21 Tage Aufbewahrung.
3. Unveränderliche URL-basierte IDs und quellenübergreifende Auswahl mit Obergrenze je Medienfamilie.
4. Übersetzung nur mit vorhandener Ausgabe; Zahlen- und Sprachprüfung. Bei Fehlern bleibt der Originaltitel erhalten. Diese technischen Prüfungen beweisen keine semantische Richtigkeit.
5. Tests für RSS/Atom, Datum, Sommerzeit, Quellenfilter, Sprachwechsel und Suche.
6. Vollständiger Websitebuild, auflösbare interne Links und exakt 16 Seiten pro PDF.

## Quellenausfälle

Ein fehlgeschlagener Feed blockiert die übrigen Quellen nicht. Vorhandene Beiträge bleiben nur innerhalb ihrer Aufbewahrungsfrist erhalten und tragen ihr ursprüngliches Datum. Ein vollständiger Ausfall ersetzt keine bereits gute Sammlung durch eine leere Ausgabe. `data/health.json`, der Workflowbericht und die öffentliche Statusseite zeigen den Zustand. Nach 36 Stunden ohne erfolgreiche Gesamtaktualisierung weist die Website auf den gespeicherten Stand hin.

Ein gelistetes Medium ohne Feed bleibt ein Link auf seine offizielle Website. Es wird nicht durch einen erfundenen RSS-Endpunkt oder eine Kopie aus einem anderen Medium ersetzt. Neue Feedadressen werden in `config/sources.json` eingetragen und beim nächsten Lauf geprüft. Neue YouTube-Kanäle benötigen die verifizierte kanonische Channel-ID und einen Nachweis ihrer Identität.

## Kalender

Voreinstellung Jerusalem, umstellbar auf sechs konfigurierte Städte. Die Darstellung nennt Ort, Zeitzone, Israel-/Diasporamodus und Rechenmethode. Die Zeitung übernimmt Hebcal-Daten mit Quellenangabe und CC-BY-4.0-Hinweis. Zeitdaten einer abgelaufenen Woche werden nicht als aktuell dargestellt. Die konkrete Gemeinde kann abweichende Methoden/Minhagim verwenden.

## Korrekturen

Aktuelle Quelldaten können neu eingesammelt werden; die Behauptung bleibt der Originalquelle zugerechnet. Ein erheblicher Fehler in einer veröffentlichten Wochenedition erfordert eine neue Ausgabe-ID mit dokumentierter Revision, die ursprüngliche unverändert erhaltene Ausgabe und einen sichtbaren Berichtigungshinweis. Beide Sprachfassungen prüfen. Menschliche oder rabbinische Freigaben dürfen nur mit tatsächlichem Prüfer und passender Textrevision eingetragen werden.

## Technische Grenzen

GitHub Actions ist kein Echtzeitdienst; Takte und Publikation können sich verzögern. Übersetzungsmodelle können Namen, Idiome und Fachbegriffe falsch behandeln. Ein RSS-Feed ist kein Nachdruckrecht für vollständige Artikel. Videos und Untertitel können regional oder durch den Rechteinhaber eingeschränkt sein. Die Zeitung ist kein Warnsystem und erteilt keine individuellen medizinischen, rechtlichen oder halakhischen Entscheidungen.

Der öffentliche Standardbetrieb benötigt keine bezahlten KI-Aufrufe. Öffentliche Standardrunner sind von den GitHub-Konditionen abhängig; private Vorschauen verbrauchen gegebenenfalls das private Actions-Kontingent. Bei dauerhaftem Verzicht auf private Vorschauen kann deren Schedule deaktiviert werden, ohne die öffentliche Zeitung anzuhalten.

## Prüfquellen zur Einrichtung, 24.10.2026

- JPost RSS und ausdrücklicher RSS-Abschnitt der Nutzungsbedingungen: https://www.jpost.com/rss ; https://www.jpost.com/landedpages/termsofservice.aspx
- Hebcal Kalender, Shabbat- und Lernoptionen: https://www.hebcal.com/home/developer-apis ; https://www.hebcal.com/home/195/jewish-calendar-rest-api
- Offizieller Argos-Modellkatalog: https://github.com/argosopentech/argospm-index
- CTranslate2: https://opennmt.net/CTranslate2/
- GitHub Pages Aktivierung: `actions/configure-pages` verlangt zur erstmaligen automatischen Aktivierung einen anderen Token als GITHUB_TOKEN. Deshalb Aktivierung über Settings → Pages oder vorhandenen Administratorzugang.
- GitHub Models wurde eingestellt; der Standardbetrieb verwendet diesen Dienst nicht: https://docs.github.com/en/github-models
