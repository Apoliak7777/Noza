"""Vyrobí obrázky na zdieľanie (og:image 1200×630) pre SK aj DE: web/img/og-sk.jpg, web/img/og-de.jpg.
Podklad je hero fotka stmavená do petrolovej, vľavo logo a titulok. Spustenie: python nastroje/og_obrazok.py
Značka je len „NOZA“ (klient má viac s. r. o. s Noza v názve, konkrétna firma je len v pätičke webu).
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

KDE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(KDE, "web", "img")
FONT = os.path.join(KDE, "web", "fonts", "archivo-latin-ext.woff2")  # variabilný font, PIL ho vie čítať
W, H = 1200, 630

# jazyk: (titulok, podtitulok, riadok pod značkou)
TEXTY = {
    "sk": ("Montážne tímy pre stavby\npo celom Nemecku", "Vzduchotechnika · Sadrokartón · Montážne práce", "MONTÁŽNA FIRMA"),
    "de": ("Montageteams für Baustellen\nin ganz Deutschland", "Lüftungstechnik · Trockenbau · Montagearbeiten", "MONTAGEUNTERNEHMEN"),
}


def font(velkost):
    for cesta in (FONT, "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        try:
            f = ImageFont.truetype(cesta, velkost)
            try:
                f.set_variation_by_axes([110, 800])  # wdth, wght (ak je font variabilný)
            except Exception:
                pass
            return f
        except Exception:
            continue
    return ImageFont.load_default()


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
        d.text((250, 84), "NOZA", font=font(54), fill=(255, 255, 255))
        d.text((252, 150), znacka, font=font(22), fill=(25, 183, 214))
        d.multiline_text((80, 280), titulok, font=font(64), fill=(255, 255, 255), spacing=10)
        d.rectangle((80, 470, 140, 476), fill=(25, 183, 214))
        d.text((80, 500), podtitulok, font=font(28), fill=(223, 234, 238))
        cesta = os.path.join(IMG, f"og-{jazyk}.jpg")
        im.save(cesta, "JPEG", quality=86, optimize=True)
        print(cesta, os.path.getsize(cesta) // 1024, "kB")


if __name__ == "__main__":
    main()
