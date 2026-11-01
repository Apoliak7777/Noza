"""Vyrobí všetky obrázky webu z pôvodných fotiek v podklady/fotky_povodne/.

Spustenie:  python nastroje/obrazky.py   (z koreňa projektu, alebo odkiaľkoľvek)

Čo robí:
  * z každej fotky odreže čierne pásy (niektoré sú screenshoty z mobilu),
  * (galériu realizácií robí nastroje/realizacie.py, zoznam FOTKY nižšie už len popisuje pôvodné fotky),
  * vyrobí hero fotku (1920 px) a fotky pre karty služieb,
  * z loga so bielym pozadím spraví priehľadné PNG (logo aj samotný symbol) a ikony.

Fotky sa nikdy neupravujú ručne — zmení sa tento skript a pustí sa znova.
"""
import os
from PIL import Image

KDE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZDROJ = os.path.join(KDE, "podklady", "fotky_povodne")
CIEL = os.path.join(KDE, "web", "img")

# poradie v galérii + slug (podľa obsahu fotky)
FOTKY = [
    ("489C16F6-E6BF-465D-A0E6-6216DD855336", "montaz-z-plosiny"),
    ("23A11BE0-A1E9-497B-B57B-8577071527EB", "vzt-pod-stropom"),
    ("76340F61-5444-49D8-A19C-F1A9B368EC0C", "zeriav-vzt-jednotka"),
    ("0E3DAF90-54B4-4A3A-BD61-BD864F0D95D6", "rozvody-a-sadrokarton"),
    ("523B484D-A05F-442C-B07F-249F0D8BB945", "potrubie-detail"),
    ("A768640E-0CD0-425B-9E15-BA09616D1669", "montaznik-v-hale"),
    ("20705EFD-E545-45A8-B725-86D250207A71", "hala-rozvody"),
    ("16BF1081-7091-4520-B201-0F98D404D5FD", "spiro-potrubie"),
    ("681206FF-F5E9-4DD2-B77C-7C1D2C6F2C76", "miestnost-rozvody"),
    ("2F472E78-F97A-49EE-9E60-32F1B4A026B6", "kruhove-potrubie"),
    ("546DC383-B44B-4DA4-A124-2B28D7942477", "hala-vecer"),
    ("40DD1498-9DD6-481E-B6F6-C988B1C96DFF", "nozicova-plosina"),
    ("51DCFC71-2818-480C-AB66-41E41DF1FB03", "chodba-rozvody"),
    ("5F7908F3-7063-4D72-8E4A-E3931261A977", "zavesene-potrubie"),
    ("33C7F408-27C3-4F24-9578-43011F69B899", "plosina-v-hale"),
    ("450960BA-4681-49F1-A2F4-5D67CDDE5D64", "rozvody-strop"),
    ("57917CEB-B93B-44E5-82D0-C39BA9BFA464", "hala-osvetlenie"),
    ("3C7564FC-77D1-4713-AE06-87585663087B", "hranate-potrubie"),
    ("826F6D97-FA45-4F7F-A8A6-3394FDF17D54", "schodisko-montaz"),
]

HERO = "23A11BE0-A1E9-497B-B57B-8577071527EB"          # svetlá hala, rozvody pod stropom, denné svetlo
ONAS = "489C16F6-E6BF-465D-A0E6-6216DD855336"          # montážnik na plošine
SLUZBY = {                                              # karty služieb
    "vzduchotechnika": "../realizacie/straubing/003_143638.jpg",   # VZT jednotka s montážnikom (Straubing)
    "sadrokarton": "../realizacie/sadrokarton/010_142613.jpg",     # rošt kazetového stropu a sadrokartónové steny
    "montaz": "76340F61-5444-49D8-A19C-F1A9B368EC0C",              # osadenie jednotky žeriavom
    "partneri": "../realizacie/kempinski/019_143522.jpg",          # tím pri práci v hoteli Kempinski
}
LOGO = "logo_noza_4m_povodne.png"


def orez_cierne_pasy(im, prah=16):
    """Odreže čierne vodorovné pásy hore a dole (screenshoty z mobilu)."""
    g = im.convert("L")
    w, h = g.size
    px = g.load()

    def tmavy_riadok(y):
        return sum(px[x, y] for x in range(0, w, 4)) / (w / 4) < prah

    hore = 0
    while hore < h // 3 and tmavy_riadok(hore):
        hore += 1
    dole = h
    while dole > 2 * h // 3 and tmavy_riadok(dole - 1):
        dole -= 1
    if hore or dole != h:
        im = im.crop((0, hore, w, dole))
    return im


def zmensi(im, max_strana):
    im = im.copy()
    im.thumbnail((max_strana, max_strana), Image.LANCZOS)
    return im


def uloz_webp(im, cesta, kvalita):
    im.convert("RGB").save(cesta, "WEBP", quality=kvalita, method=6)
    return os.path.getsize(cesta)


def nacitaj(nazov):
    """Pôvodná fotka zo starého webu (meno bez prípony) alebo cesta k fotke klienta (s lomkou)."""
    from PIL import ImageOps
    cesta = os.path.normpath(os.path.join(ZDROJ, nazov)) if "/" in nazov else os.path.join(ZDROJ, nazov + ".webp")
    return orez_cierne_pasy(ImageOps.exif_transpose(Image.open(cesta)).convert("RGB"))


def orez_na_pomer(im, pomer, ohnisko_y=0.5):
    """Vyreže z fotky výrez s daným pomerom strán (šírka/výška), ohnisko zvislo 0–1."""
    w, h = im.size
    if w / h > pomer:  # príliš široká → orež boky
        nw = int(h * pomer)
        x0 = (w - nw) // 2
        return im.crop((x0, 0, x0 + nw, h))
    nh = int(w / pomer)  # príliš vysoká → orež hore/dole podľa ohniska
    y0 = int((h - nh) * ohnisko_y)
    return im.crop((0, y0, w, y0 + nh))


def logo_priehladne():
    """Biele pozadie loga → priehľadnosť. Farby loga majú vždy jeden kanál na nule,
    takže alfa = 255 - min(r,g,b) a farba sa dá spätne 'odmiešať' od bielej."""
    im = Image.open(os.path.join(ZDROJ, LOGO)).convert("RGB")
    w, h = im.size
    out = Image.new("RGBA", (w, h))
    src, dst = im.load(), out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = src[x, y]
            a = 255 - min(r, g, b)
            if a == 0:
                dst[x, y] = (0, 0, 0, 0)
                continue
            k = a / 255
            dst[x, y] = (
                max(0, min(255, round((r - (1 - k) * 255) / k))),
                max(0, min(255, round((g - (1 - k) * 255) / k))),
                max(0, min(255, round((b - (1 - k) * 255) / k))),
                a,
            )
    bbox = out.getbbox()
    out = out.crop(bbox)
    # symbol bez nápisu: nájdi najväčšiu bielu medzeru v dolnej tretine
    alfa = out.split()[3]
    w, h = alfa.size
    px = alfa.load()
    prazdne = [all(px[x, y] == 0 for x in range(0, w, 2)) for y in range(h)]
    delitel = None
    y = int(h * 0.6)
    while y < h:
        if prazdne[y]:
            zac = y
            while y < h and prazdne[y]:
                y += 1
            if y - zac > 8:
                delitel = (zac + y) // 2
                break
        y += 1
    symbol = out.crop((0, 0, w, delitel)).crop(out.crop((0, 0, w, delitel)).getbbox()) if delitel else out
    return out, symbol


def main():
    hero = orez_na_pomer(nacitaj(HERO), 16 / 9, 0.45)
    print("hero:", uloz_webp(zmensi(hero, 1920), os.path.join(CIEL, "hero.webp"), 80) // 1024, "kB")
    hero_m = orez_na_pomer(nacitaj(HERO), 4 / 5, 0.45)
    print("hero-m:", uloz_webp(zmensi(hero_m, 900), os.path.join(CIEL, "hero-m.webp"), 76) // 1024, "kB")

    onas = orez_na_pomer(nacitaj(ONAS), 4 / 5, 0.4)
    print("o-nas:", uloz_webp(zmensi(onas, 1000), os.path.join(CIEL, "o-nas.webp"), 78) // 1024, "kB")

    for nazov, subor in SLUZBY.items():
        im = orez_na_pomer(nacitaj(subor), 4 / 3, 0.35)
        print(f"sluzba-{nazov}:", uloz_webp(zmensi(im, 900), os.path.join(CIEL, f"sluzba-{nazov}.webp"), 76) // 1024, "kB")

    logo, symbol = logo_priehladne()
    logo.save(os.path.join(CIEL, "logo.png"), optimize=True)
    symbol.save(os.path.join(CIEL, "logo-symbol.png"), optimize=True)
    print("logo:", logo.size, "symbol:", symbol.size)
    for velkost, nazov in ((32, "favicon-32.png"), (180, "apple-touch-icon.png"), (512, "icon-512.png")):
        ik = Image.new("RGBA", (velkost, velkost), (0, 0, 0, 0))
        s = symbol.copy()
        s.thumbnail((int(velkost * 0.9), int(velkost * 0.9)), Image.LANCZOS)
        ik.paste(s, ((velkost - s.size[0]) // 2, (velkost - s.size[1]) // 2), s)
        ik.save(os.path.join(CIEL, nazov), optimize=True)
    print("ikony hotové")


if __name__ == "__main__":
    main()
