"""Vyrobí noza-web.zip na nahratie na hosting: obsah priečinka web/ priamo v koreni zipu."""
import os, zipfile
KDE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(KDE, "web")
ZIP = os.path.join(KDE, "noza-web.zip")
VYNECHAJ = {".DS_Store", "Thumbs.db"}
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for koren, priecinky, subory in os.walk(WEB):
        for s in sorted(subory):
            if s in VYNECHAJ:
                continue
            cela = os.path.join(koren, s)
            z.write(cela, os.path.relpath(cela, WEB).replace(os.sep, "/"))
with zipfile.ZipFile(ZIP) as z:
    n = len(z.infolist())
print("hotovo:", ZIP, os.path.getsize(ZIP) // 1024, "kB,", n, "súborov")
