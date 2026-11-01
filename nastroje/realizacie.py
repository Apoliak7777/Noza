"""Realizácie (podskupiny fotiek) — z priečinkov s fotkami vyrobí galérie na webe, SK aj DE.

Spustenie:  python nastroje/realizacie.py

Vstup:
  podklady/realizacie/projekty.json   zoznam realizácií, poradie, texty SK/DE (nazov, stitok, popis)
  podklady/realizacie/<id>/           fotky realizácie (jpg, jpeg, png, webp, heic), poradie podľa názvu súboru
  "fotky_navyse" v projekty.json      fotky z inej cesty aj s popisom (staré fotky zo starého noza.sk)

Výstup:
  web/img/realizacie/<id>/NNN.webp    veľká verzia (dlhšia strana max 2400 px) – otvára sa v lightboxe a v plnom rozlíšení
  web/img/realizacie/<id>/NNN-t.webp  zmenšenina do mriežky
  web/img/realizacie/<id>/obal.webp   obal karty 4:3
  web/sk/realizacie/<slug>/index.html, web/de/referenzen/<slug>/index.html   stránka realizácie
  karty v sekcii Realizácie v web/sk/index.html a web/de/index.html (medzi značkami REALIZACIE:START/END)
  web/sitemap.xml

Duplicitné fotky (aj tie, čo už boli na starom webe) spozná podľa obsahu a vynechá ich. Realizácia bez fotiek
sa na web nedostane. Hlavička a pätička stránok realizácií sa berú z hlavnej stránky, takže ostávajú zhodné.
"""
import glob
import html
import json
import os
import re
import sys

from PIL import Image, ImageOps

try:  # fotky z iPhonu
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass

KDE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PODKLADY = os.path.join(KDE, "podklady", "realizacie")
WEB = os.path.join(KDE, "web")
DOMENA = "https://www.noza.sk"
PRIPONY = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif")
VELKA, MALA, OBAL = 2400, 640, (960, 720)
PRAH_DUPLICITY = 6  # rozdiel bitov dHash, pod ktorým sú dve fotky tá istá fotka

JAZYKY = {
    "sk": {
        "cesta": "realizacie", "kotva": "referencie", "domov_label": "NOZA — domov", "menu": "Hlavné menu",
        "lightbox": "Fotka na celú obrazovku", "pred": "Predchádzajúca", "dalsia": "Ďalšia", "zavriet": "Zavrieť",
        "plne": "Otvoriť v plnom rozlíšení", "crumbs": "Realizácie", "dalsie": "Ďalšie realizácie",
        "cta_h": "Máte podobnú stavbu?", "cta_p": "Napíšte nám rozsah prác, miesto a termín. Ozveme sa vám späť.",
        "cta_btn": "Poslať dopyt", "hint": "Kliknite na fotku, otvorí sa vo veľkom.", "fotka": "Fotka",
        "title": "{n} — realizácie | NOZA", "desc": "{n}: {p} zo stavieb firmy NOZA v Nemecku. Vzduchotechnika, sadrokartón a montážne práce.",
    },
    "de": {
        "cesta": "referenzen", "kotva": "referenzen", "domov_label": "NOZA – Startseite", "menu": "Hauptmenü",
        "lightbox": "Foto in Vollansicht", "pred": "Zurück", "dalsia": "Weiter", "zavriet": "Schließen",
        "plne": "In voller Auflösung öffnen", "crumbs": "Referenzen", "dalsie": "Weitere Referenzen",
        "cta_h": "Sie haben ein ähnliches Projekt?", "cta_p": "Schicken Sie uns Leistungsumfang, Baustelle und Termin. Wir melden uns zurück.",
        "cta_btn": "Anfrage senden", "hint": "Klicken Sie auf ein Foto, um es groß anzuzeigen.", "fotka": "Foto",
        "title": "{n} – Referenzen | NOZA", "desc": "{n}: {p} von Baustellen der Firma NOZA in Deutschland. Lüftungstechnik, Trockenbau und Montage.",
    },
}

SIPKA = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
         'stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>')
IKONA_PLNE = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
              'stroke-linejoin="round" aria-hidden="true"><path d="M14 4h6v6M10 20H4v-6M20 4l-7 7M4 20l7-7"/></svg>')


def pocet_fotiek(n, jazyk):
    if jazyk == "de":
        return f"{n} Foto" if n == 1 else f"{n} Fotos"
    if n == 1:
        return "1 fotka"
    return f"{n} fotky" if 2 <= n <= 4 else f"{n} fotiek"


def pocet_realizacii(n, jazyk):
    if jazyk == "de":
        return f"{n} Referenz" if n == 1 else f"{n} Referenzen"
    if n == 1:
        return "1 realizácia"
    return f"{n} realizácie" if 2 <= n <= 4 else f"{n} realizácií"


def esc(t):
    return html.escape(t or "", quote=True)


# ---------------------------------------------------------------- fotky
def dhash(im, velkost=8):
    g = im.convert("L").resize((velkost + 1, velkost), Image.LANCZOS)
    px = list(g.tobytes())
    bity = 0
    for r in range(velkost):
        for s in range(velkost):
            bity = (bity << 1) | (px[r * (velkost + 1) + s] > px[r * (velkost + 1) + s + 1])
    return bity


def orez_pasy(im):
    """Screenshot z mobilu má hore aj dole čierny pás (so stavovým riadkom a tlačidlami). Oreže ich,
    len keď sú pásy hore aj dole a medzi nimi ostane obsah — tmavé nočné fotky nechá tak."""
    import numpy as np
    a = np.asarray(im.convert("L"), dtype=np.uint8)
    h = a.shape[0]
    priemer = a.mean(axis=1)
    jasne = (a > 60).mean(axis=1)
    pas = (priemer < 22) & (jasne < 0.12)
    hore = 0
    while hore < h * 0.48 and pas[hore]:
        hore += 1
    dole = h
    while dole > h * 0.52 and pas[dole - 1]:
        dole -= 1
    if hore >= h * 0.06 and (h - dole) >= h * 0.06 and dole - hore > h * 0.15:
        return im.crop((0, hore, im.width, dole))
    return im


def nacitaj(cesta):
    im = Image.open(cesta)
    im = ImageOps.exif_transpose(im)
    return orez_pasy(im.convert("RGB"))


def fotky_projektu(p):
    """Zoznam (cesta, popis_sk, popis_de) v poradí: priečinok realizácie, potom fotky_navyse."""
    vysledok = []
    priecinok = os.path.join(PODKLADY, p["id"])
    if os.path.isdir(priecinok):
        for f in sorted(os.listdir(priecinok)):
            if f.lower().endswith(PRIPONY):
                vysledok.append((os.path.join(priecinok, f), "", ""))
    for x in p.get("fotky_navyse", []):
        vysledok.append((os.path.normpath(os.path.join(PODKLADY, x["subor"])), x.get("sk", ""), x.get("de", "")))
    return vysledok


def spracuj_fotky(projekty):
    """Vyrobí webp verzie, vynechá duplicity. Vráti {id: [ {n, w, h, tw, th, sk, de} ]}."""
    videne = []  # (hash, id, zdroj)
    vysledok = {}
    for p in projekty:
        ciel = os.path.join(WEB, "img", "realizacie", p["id"])
        os.makedirs(ciel, exist_ok=True)
        for stary in glob.glob(os.path.join(ciel, "*.webp")):  # vygenerované výstupy, vyrobia sa znova
            os.remove(stary)
        polozky = []
        for cesta, popis_sk, popis_de in fotky_projektu(p):
            try:
                im = nacitaj(cesta)
            except Exception as e:
                print(f"  ! {os.path.basename(cesta)}: nedá sa otvoriť ({e})")
                continue
            h = dhash(im)
            dup = next((v for v in videne if bin(v[0] ^ h).count("1") <= PRAH_DUPLICITY), None)
            if dup:
                print(f"  = {p['id']}: {os.path.basename(cesta)} je duplicita fotky {os.path.basename(dup[2])} ({dup[1]}), vynechaná")
                continue
            videne.append((h, p["id"], cesta))
            n = len(polozky) + 1
            velka = im.copy()
            velka.thumbnail((VELKA, VELKA), Image.LANCZOS)
            velka.save(os.path.join(ciel, f"{n:03d}.webp"), "WEBP", quality=84, method=4)
            mala = im.copy()
            mala.thumbnail((MALA, MALA), Image.LANCZOS)
            mala.save(os.path.join(ciel, f"{n:03d}-t.webp"), "WEBP", quality=72, method=4)
            polozky.append({"n": n, "w": velka.width, "h": velka.height, "tw": mala.width, "th": mala.height,
                            "sk": popis_sk, "de": popis_de, "zdroj": cesta})
        if polozky:
            obal = p.get("obal", 1)
            if isinstance(obal, str):  # meno súboru v priečinku realizácie
                obal_i = next((i for i, f in enumerate(polozky) if os.path.basename(f["zdroj"]) == obal), 0)
            else:
                obal_i = min(max(int(obal), 1), len(polozky)) - 1
            im = nacitaj(polozky[obal_i]["zdroj"])
            ImageOps.fit(im, OBAL, Image.LANCZOS, centering=(0.5, float(p.get("obal_vyska", 0.45)))).save(
                os.path.join(ciel, "obal.webp"), "WEBP", quality=78, method=4)
        vysledok[p["id"]] = polozky
        print(f"  {p['id']}: {len(polozky)} fotiek")
    return vysledok


# ---------------------------------------------------------------- HTML
def vystrihni(s, zaciatok, koniec):
    i = s.index(zaciatok)
    j = s.index(koniec, i) + len(koniec)
    return s[i:j]


def posun_odkazy(fragment, predpona):
    """Relatívne odkazy z hlavnej stránky prepíše tak, aby fungovali o dve úrovne hlbšie."""
    def nahrad(m):
        attr, url = m.group(1), m.group(2)
        if re.match(r"^(https?:|mailto:|tel:|data:|//)", url):
            return m.group(0)
        return f'{attr}="{predpona}{url}"'
    return re.sub(r'(href|src)="([^"]*)"', nahrad, fragment)


def karta(p, jazyk, pocet, odkaz, obrazok, reveal=True):
    t = p[jazyk]
    trieda = "projekt reveal" if reveal else "projekt"
    return (f'<a class="{trieda}" href="{odkaz}">'
            f'<img src="{obrazok}" alt="" loading="lazy" width="{OBAL[0]}" height="{OBAL[1]}">'
            f'<span class="projekt-body"><span class="projekt-stitok">{esc(t["stitok"])}</span>'
            f'<span class="projekt-nazov">{esc(t["nazov"])}</span>'
            f'<span class="projekt-pocet">{pocet_fotiek(pocet, jazyk)} {SIPKA}</span></span></a>')


def stranka_realizacie(p, jazyk, polozky, projekty, fotky, hlavicka, paticka):
    T = JAZYKY[jazyk]
    t = p[jazyk]
    druhy = "de" if jazyk == "sk" else "sk"
    koren = "../../../"
    url = f"{DOMENA}/{jazyk}/{T['cesta']}/{t['slug']}/"
    url_druhy = f"{DOMENA}/{druhy}/{JAZYKY[druhy]['cesta']}/{p[druhy]['slug']}/"
    obr = f"{koren}img/realizacie/{p['id']}/"

    # hlavička z hlavnej stránky: plná, prepínač jazyka mieri na tú istú realizáciu
    h = hlavicka.replace('<header class="top">', '<header class="top page-top">')
    h = re.sub(r'<span class="lang"[\s\S]*?</span>\s*</nav>',
               (f'<span class="lang" aria-label="{"Jazyk" if jazyk == "sk" else "Sprache"}">'
                + (f'<a href="./" aria-current="true" hreflang="sk" lang="sk">SK</a>'
                   f'<a href="{koren}de/referenzen/{p["de"]["slug"]}/" hreflang="de" lang="de">DE</a>' if jazyk == "sk" else
                   f'<a href="{koren}sk/realizacie/{p["sk"]["slug"]}/" hreflang="sk" lang="sk">SK</a>'
                   f'<a href="./" aria-current="true" hreflang="de" lang="de">DE</a>')
                + '</span>\n    </nav>'), h)

    mriezka = []
    for f in polozky:
        popis = f[jazyk] or f"{t['nazov']} – {T['fotka'].lower()} {f['n']}"
        mriezka.append(
            f'<a href="{obr}{f["n"]:03d}.webp" data-popis="{esc(f[jazyk])}" data-w="{f["w"]}" data-h="{f["h"]}">'
            f'<img src="{obr}{f["n"]:03d}-t.webp" alt="{esc(popis)}" loading="lazy" decoding="async" '
            f'width="{f["tw"]}" height="{f["th"]}"></a>')

    ine = [q for q in projekty if q["id"] != p["id"] and fotky.get(q["id"])]
    karty_ine = "".join(
        karta(q, jazyk, len(fotky[q["id"]]), f"../{q[jazyk]['slug']}/", f"{koren}img/realizacie/{q['id']}/obal.webp", reveal=False)
        for q in ine)

    pocet = pocet_fotiek(len(polozky), jazyk)
    popis_html = f'<p class="lead">{esc(t["popis"])}</p>' if t.get("popis") else ""
    title = T["title"].format(n=t["nazov"])
    desc = T["desc"].format(n=t["nazov"], p=pocet)
    return f"""<!DOCTYPE html>
<html lang="{jazyk}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="{jazyk}" href="{url}">
<link rel="alternate" hreflang="{druhy}" href="{url_druhy}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="NOZA">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{DOMENA}/img/realizacie/{p['id']}/obal.webp">
<meta name="theme-color" content="#063947">
<link rel="icon" href="{koren}img/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="{koren}img/apple-touch-icon.png">
<link rel="preload" href="{koren}fonts/archivo-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{koren}fonts/archivo-latin-ext.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{koren}styles.css">
</head>
<body data-lang="{jazyk}" class="stranka-realizacie">
{h}

<main class="page section">
  <div class="wrap">
    <nav class="crumbs" aria-label="{"Navigácia" if jazyk == "sk" else "Navigation"}"><a href="../../#{T['kotva']}">{T['crumbs']}</a><span aria-hidden="true">/</span><span>{esc(t['nazov'])}</span></nav>
    <div class="projekt-head">
      <p class="eyebrow">{esc(t['stitok'])}</p>
      <h1>{esc(t['nazov'])}</h1>
      {popis_html}
      <p class="projekt-meta"><strong>{pocet}</strong><span>{T['hint']}</span></p>
    </div>
    <div class="foto-grid">
      {chr(10).join("      " + m for m in mriezka).lstrip()}
    </div>
{f'''
    <section class="dalsie" aria-labelledby="dalsie-h">
      <h2 id="dalsie-h">{T['dalsie']}</h2>
      <div class="projekty projekty-male">{karty_ine}</div>
    </section>''' if karty_ine else ''}

    <div class="cta-band">
      <div><h2>{T['cta_h']}</h2><p>{T['cta_p']}</p></div>
      <a class="btn btn-primary" href="../../#kontakt">{T['cta_btn']} {SIPKA}</a>
    </div>
  </div>
</main>

<dialog class="lightbox" aria-label="{T['lightbox']}">
  <figure><img src="" alt=""><figcaption><span class="lb-popis"></span><span class="lb-pocet"></span><a class="lb-full" href="" target="_blank" rel="noopener">{IKONA_PLNE} {T['plne']}</a></figcaption></figure>
  <button class="prev" type="button" aria-label="{T['pred']}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 6l-6 6 6 6"/></svg></button>
  <button class="next" type="button" aria-label="{T['dalsia']}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg></button>
  <button class="close" type="button" aria-label="{T['zavriet']}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
</dialog>

{paticka}
<script src="{koren}script.js" defer></script>
</body>
</html>
"""


def karty_na_hlavnu(projekty, fotky, jazyk):
    T = JAZYKY[jazyk]
    s_fotkami = [p for p in projekty if fotky.get(p["id"])]
    spolu = sum(len(fotky[p["id"]]) for p in s_fotkami)
    karty = "\n        ".join(
        karta(p, jazyk, len(fotky[p["id"]]), f"{T['cesta']}/{p[jazyk]['slug']}/", f"../img/realizacie/{p['id']}/obal.webp")
        for p in s_fotkami)
    return (f'<!-- REALIZACIE:START (generuje nastroje/realizacie.py, ručne needitovať) -->\n'
            f'      <p class="stat-line">{pocet_realizacii(len(s_fotkami), jazyk)} · {pocet_fotiek(spolu, jazyk)}</p>\n'
            f'      <div class="projekty">\n        {karty}\n      </div>\n'
            f'      <!-- REALIZACIE:END -->')


def sitemap(projekty, fotky):
    def url(loc, alt):
        riadky = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{j}" href="{u}"/>' for j, u in alt)
        return f"  <url>\n    <loc>{loc}</loc>{riadky}\n  </url>"
    zaznamy = []
    hlavne = [("sk", f"{DOMENA}/sk/"), ("de", f"{DOMENA}/de/"), ("x-default", f"{DOMENA}/")]
    zaznamy += [url(f"{DOMENA}/sk/", hlavne), url(f"{DOMENA}/de/", hlavne)]
    for p in projekty:
        if not fotky.get(p["id"]):
            continue
        sk = f"{DOMENA}/sk/realizacie/{p['sk']['slug']}/"
        de = f"{DOMENA}/de/referenzen/{p['de']['slug']}/"
        zaznamy += [url(sk, [("sk", sk), ("de", de)]), url(de, [("sk", sk), ("de", de)])]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + "\n".join(zaznamy) + "\n</urlset>\n")


def main():
    data = json.load(open(os.path.join(PODKLADY, "projekty.json"), encoding="utf-8"))
    projekty = data["projekty"]
    print("Fotky:")
    fotky = spracuj_fotky(projekty)
    if not any(fotky.values()):
        sys.exit("Žiadna realizácia nemá fotky.")

    for jazyk in ("sk", "de"):
        T = JAZYKY[jazyk]
        cesta_index = os.path.join(WEB, jazyk, "index.html")
        index = open(cesta_index, encoding="utf-8").read()
        index = re.sub(r"<!-- REALIZACIE:START[\s\S]*?<!-- REALIZACIE:END -->", lambda m: karty_na_hlavnu(projekty, fotky, jazyk), index)
        open(cesta_index, "w", encoding="utf-8", newline="\n").write(index)

        hlavicka = posun_odkazy(vystrihni(index, '<header class="top">', "</header>"), "../../")
        paticka = posun_odkazy(vystrihni(index, '<footer class="foot">', "</footer>"), "../../")

        koren_jazyka = os.path.join(WEB, jazyk, T["cesta"])
        for p in projekty:
            polozky = fotky.get(p["id"])
            if not polozky:
                continue
            ciel = os.path.join(koren_jazyka, p[jazyk]["slug"])
            os.makedirs(ciel, exist_ok=True)
            open(os.path.join(ciel, "index.html"), "w", encoding="utf-8", newline="\n").write(
                stranka_realizacie(p, jazyk, polozky, projekty, fotky, hlavicka, paticka))

    open(os.path.join(WEB, "sitemap.xml"), "w", encoding="utf-8", newline="\n").write(sitemap(projekty, fotky))
    s_fotkami = [p["id"] for p in projekty if fotky.get(p["id"])]
    bez = [p["id"] for p in projekty if not fotky.get(p["id"])]
    print(f"Hotovo: realizácie na webe: {len(s_fotkami)} ({', '.join(s_fotkami)}), spolu {sum(len(v) for v in fotky.values())} fotiek.")
    if bez:
        print(f"Bez fotiek (na webe nie sú): {', '.join(bez)} – fotky patria do podklady/realizacie/<id>/")


if __name__ == "__main__":
    main()
