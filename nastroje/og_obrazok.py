"""Vyrobí obrázky na zdieľanie (og:image 1200×630) pre SK aj DE: web/img/og-sk.jpg, web/img/og-de.jpg.
Podklad je hero fotka stmavená do petrolovej, vľavo logo a titulok. Spustenie: python nastroje/og_obrazok.py
Značka je len „NOZA“ (klient má viac s. r. o. s Noza v názve, konkrétna firma je len v pätičke webu).

Písmo (oprava 26.11.2026): Archivo je na webe rozdelené na dve podmnožiny – archivo-latin.woff2 (a–z, á, é, ä, ü, ·)
a archivo-latin-ext.woff2 (č, š, ž, ľ, ť, ň …). Prehliadač si podľa unicode-range vyberie sám, PIL nie – preto sa tu
písmo vyberá pre každý znak zvlášť. Do 26.11. sa bralo len latin-ext a všetky bežné písmená boli prázdne štvorčeky.
Osi variabilného písma sú v poradí Weight, Width – nastavujú sa podľa mena, nie podľa poradia.
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

KDE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(KDE, "web", "img")
FONTY = [os.path.join(KDE, "web", "fonts", "archivo-latin.woff2"),       # základná latinka, má prednosť
         os.path.join(KDE, "web", "fonts", "archivo-latin-ext.woff2")]   # slovenské a ďalšie rozšírené znaky
NAHRADNE = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"]
W, H = 1200, 630
SIRKA = 110  # Width písma Archivo (ako font-stretch nadpisov na webe)

# jazyk: (titulok, podtitulok, riadok pod značkou)
TEXTY = {
    "sk": ("Montážne tímy pre stavby\npo celom Nemecku", "Vzduchotechnika · Sadrokartón · Montážne práce", "MONTÁŽNA FIRMA"),
    "de": ("Montageteams für Baustellen\nin ganz Deutschland", "Lüftungstechnik · Trockenbau · Montagearbeiten", "MONTAGEUNTERNEHMEN"),
}

_fonty, _notdef = {}, {}


def fonty(velkost, hrubka):
    """Obe podmnožiny Archiva v danej veľkosti a hrúbke; keď sa nedajú načítať, jedno náhradné systémové písmo."""
    kluc = (velkost, hrubka)
    if kluc not in _fonty:
        sada = []
        for cesta in FONTY:
            try:
                f = ImageFont.truetype(cesta, velkost)
                hodnoty = {"Weight": hrubka, "Width": SIRKA}
                f.set_variation_by_axes([hodnoty.get(os_["name"].decode() if isinstance(os_["name"], bytes) else os_["name"],
                                                     os_["default"]) for os_ in f.get_variation_axes()])
                sada.append(f)
            except Exception as e:
                print(f"  ! {os.path.basename(cesta)}: {e}")
        if not sada:
            for cesta in NAHRADNE:
                if os.path.exists(cesta):
                    sada = [ImageFont.truetype(cesta, velkost)]
                    break
        _fonty[kluc] = sada or [ImageFont.load_default()]
    return _fonty[kluc]


def ma_znak(f, znak):
    """Chýbajúci znak FreeType nakreslí ako .notdef (prázdny obdĺžnik) – porovná sa s ním."""
    if znak.isspace():
        return True
    if f not in _notdef:
        m = f.getmask("\ue000")  # súkromná oblasť Unicode, v písme nie je nikdy
        _notdef[f] = (m.size, bytes(m))
    m = f.getmask(znak)
    return (m.size, bytes(m)) != _notdef[f]


def useky(riadok, sada):
    """Rozdelí riadok na úseky po sebe idúcich znakov, ktoré má to isté písmo (prvé v sade, ktoré znak má)."""
    vysledok = []
    for znak in riadok:
        f = next((x for x in sada if ma_znak(x, znak)), None)
        if f is None:
            print(f"  ! znak {znak!r} nie je v žiadnom písme")
            f = sada[0]
        if vysledok and vysledok[-1][0] is f:
            vysledok[-1][1] += znak
        else:
            vysledok.append([f, znak])
    return vysledok


def text(d, xy, retazec, velkost, fill, hrubka=800, riadkovanie=10, rozostup=0):
    """Ako ImageDraw.multiline_text, ale s výberom písma pre každý znak; rozostup = medzera medzi písmenami v px."""
    sada = fonty(velkost, hrubka)
    x0, y = xy
    vyska_riadku = d.textbbox((0, 0), "A", font=sada[0])[3] + riadkovanie
    for riadok in retazec.split("\n"):
        x = x0
        for f, kus in useky(riadok, sada):
            for cast in (kus if rozostup else [kus]):
                d.text((x, y), cast, font=f, fill=fill)
                x += f.getlength(cast) + rozostup
        y += vyska_riadku
    return y


def main():
    hero = Image.open(os.path.join(IMG, "hero.webp")).convert("RGB")
    hero = hero.resize((W, int(W * hero.size[1] / hero.size[0])), Image.LANCZOS)
    y0 = max(0, (hero.size[1] - H) // 2)
    hero = hero.crop((0, y0, W, y0 + H)).filter(ImageFilter.GaussianBlur(1.2))
    prekryv = Image.new("RGB", (W, H), (6, 57, 71))
    podklad = Image.blend(hero, prekryv, 0.72)
    # tmavší gradient vľavo
    grad = Image.new("L", (W, 1))
    for x in range(W):
        grad.putpixel((x, 0), int(255 * min(1, max(0, (x - 250) / 700))))
    grad = grad.resize((W, H))
    podklad = Image.composite(podklad, Image.new("RGB", (W, H), (4, 28, 34)), grad)

    logo = Image.open(os.path.join(IMG, "logo-symbol.png")).convert("RGBA")
    logo.thumbnail((150, 150), Image.LANCZOS)

    for jazyk, (titulok, podtitulok, znacka) in TEXTY.items():
        im = podklad.copy()
        d = ImageDraw.Draw(im)
        im.paste(logo, (80, 70), logo)
        text(d, (250, 84), "NOZA", 54, (255, 255, 255))
        text(d, (252, 150), znacka, 22, (25, 183, 214), hrubka=700, rozostup=3)
        text(d, (80, 280), titulok, 64, (255, 255, 255))
        d.rectangle((80, 470, 140, 476), fill=(25, 183, 214))
        text(d, (80, 500), podtitulok, 28, (223, 234, 238), hrubka=560)
        cesta = os.path.join(IMG, f"og-{jazyk}.jpg")
        im.save(cesta, "JPEG", quality=86, optimize=True)
        print(cesta, os.path.getsize(cesta) // 1024, "kB")


if __name__ == "__main__":
    main()
