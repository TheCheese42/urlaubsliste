# Urlaubsliste

Ein tolles Programm zum Verwalten hierarchialer, kategorisierten Listen. Entwickelt zum Verwalten von Urlaubslisten.
Aktuell leider nur auf deutsch und für das Windows OS.

## Kompilieren

Zum einfachen Ausführen reicht es die `urlaubsliste/__main__.py` Datei mit einem Python interpreter auszuführen (getestet `3.9.13`).
Zum kompilieren mit `nuitka` wird die `build.ps1` bereitgestellt. Vorher sollten die Dependencies installiert werden:

```python
python -m pip install -r requirements.txt
python -m pip install -r dev-requirements.txt
powershell build.ps1
```

Der build Prozess dauert häufig lange (bis zu 20 Minuten).
