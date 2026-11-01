# NOZA – www.noza.sk

Web montážnej firmy NOZA (vzduchotechnika, sadrokartón a montážne práce po celom Nemecku), slovensky a nemecky.

## Čo je kde

| Priečinok / súbor | Čo obsahuje |
|---|---|
| `web/` | hotový web: `sk/`, `de/`, obrázky, písma, `styles.css`, `script.js`, `sitemap.xml` |
| `podklady/` | pôvodné fotky webu a realizácií, zoznam realizácií s textami SK/DE (`realizacie/projekty.json`) |
| `nastroje/realizacie.py` | z fotiek v `podklady/realizacie/` vyrobí galérie realizácií na webe |
| `nastroje/obrazky.py` | vyrobí obrázky webu z pôvodných fotiek |
| `nastroje/og_obrazok.py` | obrázky na zdieľanie (og:image) pre SK aj DE |
| `nastroje/screenshoty.js` | náhľady webu a automatická kontrola stránok (Playwright) |
| `nastroje/kontrola_spustenia.py` | kontrola domény: DNS webu aj pošty, presmerovania, HTTPS |
| `nastroje/nasad.py` | zverejnenie projektu do tohto repa |
| `SPUSTIT_WEB.bat` | spustí web na počítači: http://localhost:8097/sk/ (treba Python) |
| `vyrob_zip.py` | zip obsahu `web/` na nahratie na klasický hosting |

## Zverejnenie

Každý push do vetvy `main` spustí GitHub Actions (`.github/workflows/nasadenie.yml`), ktoré nasadia priečinok `web/`
na GitHub Pages s doménou **www.noza.sk** (noza.sk presmeruje na www).

`web/kontakt.php`, `web/.htaccess` a `web/_headers` sa na GitHub Pages nenasadzujú – sú pre hosting s PHP a Apache.

## Kontaktný formulár

Na GitHub Pages formulár nič neposiela na server: po odoslaní otvorí e-mail návštevníka s vyplneným dopytom
na office@noza.sk a pod formulárom ponúkne tlačidlá Gmail, Outlook a Skopírovať text. Na hostingu s PHP stačí
vrátiť do formulára `action="../kontakt.php"` (SK aj DE) a dopyt pôjde cez server.
