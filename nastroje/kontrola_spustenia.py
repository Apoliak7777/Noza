"""Kontrola ostrého spustenia noza.sk (doména na Websupporte, web na GitHub Pages): DNS (aby nevypadla pošta),
nový web, presmerovania, zmiznutý spam po starom WordPresse.

Použitie:
  python nastroje/kontrola_spustenia.py                      pošta ostáva u HostCreators (1. krok, 10/2026)
  python nastroje/kontrola_spustenia.py --posta websupport   po presune schránok k Websupportu

Číta len verejné DNS (Google DNS cez HTTPS) a web, nič nemení. Riadky CHYBA treba opraviť;
návratový kód je 1, keď je aspoň jedna chyba.
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

DOMENA = "noza.sk"
WEB = "https://www.noza.sk"
STARY_WEB = {"193.163.77.169", "2a10:9c80::193:163:77:169"}  # starý WordPress u HostCreators
NS_WEBSUPPORT = {"ns1.websupport.sk", "ns2.websupport.sk", "ns3.websupport.sk"}
GITHUB_IP = {"185.199.108.153", "185.199.109.153", "185.199.110.153", "185.199.111.153",
             "2606:50c0:8000::153", "2606:50c0:8001::153", "2606:50c0:8002::153", "2606:50c0:8003::153"}
GITHUB_WWW = "apoliak7777.github.io"
POSTA = {
    "hostcreators": {
        "mx": {"mx1.hostcreators.sk", "mx2.hostcreators.sk"},
        "spf": ["include:_spf.hostcreators.sk"],
        "cname": {"imap": "imap.hostcreators.sk", "smtp": "smtp.hostcreators.sk", "pop3": "pop3.hostcreators.sk"},
        "srv": "autodiscover.hostcreators.sk",
    },
    "websupport": {"mx": "websupport.sk", "spf": ["include:_spf.m1.websupport.sk"], "cname": {}, "srv": None},
}
GOOGLEBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
PREHLIADAC = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"

chyby = 0


def vysledok(ok, text):
    global chyby
    if not ok:
        chyby += 1
    print(("  OK     " if ok else "  CHYBA  ") + text)


def dns(meno, typ):
    """Záznamy z Google DNS cez HTTPS (bez cache tohto PC); TXT bez úvodzoviek, mená bez bodky na konci."""
    url = "https://dns.google/resolve?" + urllib.parse.urlencode({"name": meno, "type": typ})
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.load(r)
    cislo = {"A": 1, "NS": 2, "CNAME": 5, "MX": 15, "TXT": 16, "AAAA": 28, "SRV": 33}[typ]
    vystup = []
    for z in data.get("Answer", []):
        if z["type"] != cislo:
            continue
        hodnota = z["data"]
        if typ == "TXT":
            hodnota = hodnota.replace('" "', "").strip('"')
        vystup.append(hodnota.rstrip("."))
    return vystup


class BezPresmerovania(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def stiahni(url, ua=PREHLIADAC):
    """(stav, hlavičky, text) bez nasledovania presmerovaní; pri sieťovej chybe stav 0 a text chyby."""
    opener = urllib.request.build_opener(BezPresmerovania)
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    try:
        with opener.open(req, timeout=25) as r:
            return r.status, r.headers, r.read(400_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read(50_000).decode("utf-8", "replace")
    except Exception as e:  # SSL, timeout, DNS
        return 0, {}, str(e)


def kontrola_dns(posta):
    p = POSTA[posta]
    print("DNS " + DOMENA)
    ns = set(dns(DOMENA, "NS"))
    vysledok(ns == NS_WEBSUPPORT, "menné servery: " + ", ".join(sorted(ns)) +
             ("" if ns == NS_WEBSUPPORT else "  (ešte nie Websupport)"))

    ip = dns(DOMENA, "A") + dns(DOMENA, "AAAA")
    vysledok(bool(ip) and set(ip) <= GITHUB_IP, f"{DOMENA} → {', '.join(ip) or 'nič'}" +
             ("  (stále starý web)" if STARY_WEB & set(ip) else "" if set(ip) <= GITHUB_IP else "  (nie GitHub Pages)"))
    www = dns("www." + DOMENA, "CNAME")
    vysledok(www == [GITHUB_WWW], f"www.{DOMENA} → {', '.join(www) or 'bez CNAME'} (má byť {GITHUB_WWW})")
    nahodne = f"test-{uuid.uuid4().hex[:8]}.{DOMENA}"
    ip = dns(nahodne, "A")
    vysledok(not STARY_WEB & set(ip), "*.noza.sk (hviezdička) " +
             ("ukazuje na starý server" if STARY_WEB & set(ip) else "neukazuje na starý server"))

    mx = sorted(dns(DOMENA, "MX"), key=lambda x: int(x.split()[0]))
    hostitelia = {x.split()[1] for x in mx}
    if isinstance(p["mx"], set):
        ok = hostitelia == p["mx"]
    else:
        ok = bool(hostitelia) and all(h.endswith(p["mx"]) for h in hostitelia)
    vysledok(ok, "MX (kam chodí pošta): " + (", ".join(mx) or "žiadne – POŠTA NECHODÍ"))

    spf = [t for t in dns(DOMENA, "TXT") if t.lower().startswith("v=spf1")]
    if len(spf) != 1:
        vysledok(False, f"SPF: {len(spf)} záznamov (musí byť presne jeden): {spf}")
    else:
        chyba = [x for x in p["spf"] if x not in spf[0]]
        vysledok(not chyba, "SPF: " + spf[0] + (f"  (chýba {', '.join(chyba)})" if chyba else ""))

    dmarc = [t for t in dns("_dmarc." + DOMENA, "TXT") if t.startswith("v=DMARC1")]
    vysledok(len(dmarc) == 1, "DMARC: " + (dmarc[0] if dmarc else "chýba"))

    for meno, ciel in p["cname"].items():
        cname = dns(f"{meno}.{DOMENA}", "CNAME")
        vysledok(cname == [ciel], f"{meno}.{DOMENA} → {', '.join(cname) or 'nič'}")
    if p["srv"]:
        srv = dns("_autodiscover._tcp." + DOMENA, "SRV")
        vysledok(any(x.endswith(p["srv"]) for x in srv), "autodiscover (nastavenie pošty v Outlooku): " +
                 (", ".join(srv) or "chýba"))


def kontrola_webu():
    print("Web " + WEB)
    for cesta, znak in (("/sk/", "office@noza.sk"), ("/de/", "office@noza.sk")):
        stav, hlavicky, text = stiahni(WEB + cesta)
        vysledok(stav == 200 and znak in text, f"{cesta} → {stav}" + ("" if znak in text else "  (nie je to nový web)"))

    for url, ciel in (("https://noza.sk/", WEB + "/"), ("http://www.noza.sk/", WEB + "/")):
        stav, hlavicky, text = stiahni(url)
        kam = hlavicky.get("Location", text if stav == 0 else "")
        vysledok(stav in (301, 308) and kam == ciel, f"{url} → {stav} {kam}" +
                 ("" if stav else "  (certifikát ešte nie je? GitHub → Settings → Pages → Enforce HTTPS)"))

    # GitHub Pages nevie 410 – stačí 404; koreň s parametrom dostane úvodnú stránku s noindex, Google ju vyradí
    for cesta in ("/buy-brass-01166525642-expelling", "/wp-sitemap.xml", "/sitemap_index.xml", "/kontakt.php"):
        stav, _, _ = stiahni(WEB + cesta, GOOGLEBOT)
        vysledok(stav == 404, f"spam/starý WordPress {cesta} → {stav} (má byť 404)")
    stav, _, text = stiahni(WEB + "/?top=s0p1i1r2a8l0819845&filching=gournet", GOOGLEBOT)
    vysledok(stav != 200 or "noindex" in text, f"/?top=… (spam na koreni) → {stav}, noindex: {'noindex' in text}")
    stav, _, _ = stiahni(WEB + "/?utm_source=test&fbclid=abc")
    vysledok(stav == 200, f"/?utm_source=…&fbclid=… → {stav} (reklamné odkazy musia fungovať)")

    stav, _, text = stiahni(WEB + "/sitemap.xml")
    vysledok(stav == 200 and "/sk/realizacie/" in text, f"/sitemap.xml → {stav}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    posta = "hostcreators"
    if "--posta" in sys.argv:
        posta = sys.argv[sys.argv.index("--posta") + 1]
    if posta not in POSTA:
        sys.exit("--posta hostcreators | websupport")
    kontrola_dns(posta)
    kontrola_webu()
    print()
    print("Všetko v poriadku." if not chyby else f"Chýb: {chyby} – riadky CHYBA treba opraviť.")
    print("Formulár: vyplň ho na https://www.noza.sk/sk/#kontakt – musí sa otvoriť e-mail na office@noza.sk "
          "a pod formulárom tlačidlá Gmail, Outlook, Skopírovať text.")
    sys.exit(1 if chyby else 0)


if __name__ == "__main__":
    main()
