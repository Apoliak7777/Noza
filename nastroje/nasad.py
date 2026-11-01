"""Zverejní celý projekt do verejného repa Apoliak7777/Noza; push spustí GitHub Actions, ktoré nasadia web/
na GitHub Pages s doménou www.noza.sk (push = živý web do pár minút).

Použitie:
  python nastroje/nasad.py               projekt bez súkromných poznámok do repa Noza, commit a push
  python nastroje/nasad.py --nanecisto   len vypíše, čo by zverejnil (na GitHub nesiaha)

Zverejní sa všetko, čo sleduje git tohto priečinka (aj nové, ešte necommitnuté súbory, nie však tie z .gitignore),
okrem súkromných poznámok k zákazke (README.md, ZADANIE.md) a prepisu hlasoviek. README a workflow verejného repa
sú v nastroje/verejne/. Na GitHub Pages ide len web/ bez kontakt.php, .htaccess a _headers (rieši to workflow).
Pracovná kópia verejného repa je zverejnenie/ (mimo gitu tohto priečinka). Doménu www.noza.sk drží nastavenie
Pages (Settings → Pages → Custom domain), súbor CNAME netreba.
Po zverejnení: python nastroje/kontrola_spustenia.py
"""
import os
import shutil
import subprocess
import sys
from datetime import datetime

KDE = os.path.dirname(os.path.abspath(__file__))
PROJEKT = os.path.dirname(KDE)
REPO_DIR = os.path.join(PROJEKT, "zverejnenie")
REPO = "https://github.com/Apoliak7777/Noza.git"
DOMENA = "www.noza.sk"
SUKROMNE = {"README.md", "ZADANIE.md", "nastroje/prepis_hlasoviek.py"}
VEREJNE = "nastroje/verejne/"
NAVYSE = {"README.md": VEREJNE + "README.md", ".github/workflows/nasadenie.yml": VEREJNE + "nasadenie.yml"}


def git(*args, cwd=REPO_DIR):
    return subprocess.run(["git", "-C", cwd, *args], check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout.strip()


def subory_projektu():
    """{cesta v repe Noza: cesta na disku} – projekt bez súkromných súborov, plus README a workflow verejného repa."""
    vypis = git("ls-files", "-z", "--cached", "--others", "--exclude-standard", cwd=PROJEKT)
    vystup = {}
    for rel in vypis.split("\0"):
        if rel and rel not in SUKROMNE and not rel.startswith(VEREJNE) and os.path.isfile(os.path.join(PROJEKT, rel)):
            vystup[rel] = os.path.join(PROJEKT, rel)
    for ciel, zdroj in NAVYSE.items():
        vystup[ciel] = os.path.join(PROJEKT, zdroj)
    return dict(sorted(vystup.items()))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    subory = subory_projektu()
    if "--nanecisto" in sys.argv:
        velkost = sum(os.path.getsize(z) for z in subory.values())
        webu = sum(1 for s in subory if s.startswith("web/"))
        print(f"Zverejnil by som {len(subory)} súborov ({velkost // 1024} kB, z toho web/ {webu}) do {REPO}.")
        print("Súkromné, nezverejnia sa:", ", ".join(sorted(SUKROMNE)))
        return

    # pracovná kópia repa (prvýkrát klon bez prevodu koncov riadkov), commity pod účtom Apoliak7777 (noreply adresa)
    if not os.path.isdir(os.path.join(REPO_DIR, ".git")):
        subprocess.run(["git", "-c", "core.autocrlf=false", "clone", "-q", REPO, REPO_DIR], check=True)
    git("config", "core.autocrlf", "false")
    git("config", "user.name", "Apoliak7777")
    git("config", "user.email", "167175652+Apoliak7777@users.noreply.github.com")
    # GitHub vie do repa pridať vlastný commit (napr. pri zmene v Settings) – najprv ho dobehnúť
    git("fetch", "-q", "origin")
    if "origin/main" in git("branch", "-r"):
        git("reset", "-q", "--hard", "origin/main")
    else:
        git("symbolic-ref", "HEAD", "refs/heads/main")  # nové prázdne repo

    # obsah repa = presne projekt bez súkromných poznámok (čo z projektu zmizne, zmizne aj z GitHubu)
    for meno in os.listdir(REPO_DIR):
        if meno != ".git":
            cesta = os.path.join(REPO_DIR, meno)
            shutil.rmtree(cesta) if os.path.isdir(cesta) else os.remove(cesta)
    for ciel, zdroj in subory.items():
        cesta = os.path.join(REPO_DIR, ciel)
        os.makedirs(os.path.dirname(cesta), exist_ok=True)
        shutil.copy2(zdroj, cesta)

    git("add", "-A")
    zmeny = git("status", "--porcelain")
    if not zmeny:
        print(f"Bez zmien – web na https://{DOMENA} je aktuálny.")
        return
    pocet = len(zmeny.splitlines())
    git("commit", "-q", "-m", f"Web NOZA {datetime.now():%Y-%m-%d %H:%M} ({pocet} súborov)")
    subprocess.run(["git", "-C", REPO_DIR, "push", "-q", "origin", "HEAD:main"], check=True)
    print(f"Zverejnené ({pocet} zmenených súborov) – GitHub Actions nasadí web na https://{DOMENA} do pár minút.")
    print("Priebeh: gh run list -R Apoliak7777/Noza · potom python nastroje/kontrola_spustenia.py")


if __name__ == "__main__":
    main()
