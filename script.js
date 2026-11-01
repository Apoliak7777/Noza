/* NOZA — správanie stránky: hlavička, mobilné menu, odhaľovanie sekcií, galérie realizácií s lightboxom,
   prepínač jazyka s prenosom kotvy a kontaktný formulár (kontakt.php, náhradne e-mailový klient). */
(function () {
  "use strict";
  var d = document;
  var body = d.body;
  var top = d.querySelector(".top");
  var lang = body.getAttribute("data-lang") || "sk";

  /* --- hlavička: priehľadná nad hero fotkou, plná po posune --- */
  function solid() {
    if (!top) return;
    var need = window.scrollY > 30 || top.classList.contains("page-top");
    top.classList.toggle("is-solid", need);
  }
  solid();
  window.addEventListener("scroll", solid, { passive: true });

  /* --- mobilné menu --- */
  var burger = d.querySelector(".burger");
  if (burger) {
    burger.addEventListener("click", function () {
      var open = body.classList.toggle("menu-open");
      burger.setAttribute("aria-expanded", open ? "true" : "false");
    });
    d.querySelectorAll(".nav a").forEach(function (a) {
      a.addEventListener("click", function () {
        body.classList.remove("menu-open");
        burger.setAttribute("aria-expanded", "false");
      });
    });
    d.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && body.classList.contains("menu-open")) burger.click();
    });
  }

  /* --- odhaľovanie pri posune --- */
  var reveals = d.querySelectorAll(".reveal, .step");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("is-visible"); io.unobserve(en.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.12 });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add("is-visible"); });
  }

  /* --- prepínač jazyka: prenesie aktuálnu kotvu na jej náprotivok --- */
  var MAPA = {
    sk: { uvod: "start", sluzby: "leistungen", "preco-my": "warum-wir", postup: "ablauf", "o-nas": "ueber-uns", referencie: "referenzen", partneri: "partner", kontakt: "kontakt" },
    de: { start: "uvod", leistungen: "sluzby", "warum-wir": "preco-my", ablauf: "postup", "ueber-uns": "o-nas", referenzen: "referencie", partner: "partneri", kontakt: "kontakt" }
  };
  function syncLang() {
    var h = location.hash.replace("#", "");
    if (!h) return;
    d.querySelectorAll(".lang a:not([aria-current='true'])").forEach(function (a) {
      var m = MAPA[lang] && MAPA[lang][h];
      if (m) a.href = a.href.split("#")[0] + "#" + m;
    });
  }
  syncLang();
  window.addEventListener("hashchange", syncLang);

  /* --- realizácie: mriežka fotiek + lightbox (šípky, Esc, posun prstom, plné rozlíšenie) --- */
  var mriezka = d.querySelector(".foto-grid");
  var box = d.querySelector(".lightbox");
  if (mriezka && box && typeof box.showModal === "function") {
    var items = Array.prototype.slice.call(mriezka.querySelectorAll("a"));
    var n = items.length;
    var img = box.querySelector("img");
    var popis = box.querySelector(".lb-popis");
    var pocet = box.querySelector(".lb-pocet");
    var plne = box.querySelector(".lb-full");
    var idx = 0;
    var poradie = 0;
    function show(i) {
      idx = (i + n) % n;
      var a = items[idx];
      var nahlad = a.querySelector("img");
      var moje = ++poradie;
      // najprv zmenšenina (hneď), potom ostrá veľká verzia, keď sa načíta
      img.src = nahlad.currentSrc || nahlad.src;
      img.alt = nahlad.alt;
      img.classList.add("is-loading");
      var velka = new Image();
      velka.onload = function () {
        if (moje !== poradie) return;
        img.src = velka.src;
        img.classList.remove("is-loading");
      };
      velka.src = a.href;
      popis.textContent = a.getAttribute("data-popis") || "";
      pocet.textContent = (idx + 1) + " / " + n;
      plne.href = a.href;
      new Image().src = items[(idx + 1) % n].href; // dopredu načítať ďalšiu
    }
    items.forEach(function (a, i) {
      a.addEventListener("click", function (e) {
        if (e.ctrlKey || e.metaKey || e.shiftKey) return; // nová karta funguje ako obyčajný odkaz
        e.preventDefault();
        show(i);
        box.showModal();
      });
    });
    box.querySelector(".prev").addEventListener("click", function () { show(idx - 1); });
    box.querySelector(".next").addEventListener("click", function () { show(idx + 1); });
    box.querySelector(".close").addEventListener("click", function () { box.close(); });
    box.addEventListener("click", function (e) { if (e.target === box) box.close(); });
    box.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") show(idx - 1);
      if (e.key === "ArrowRight") show(idx + 1);
    });
    var x0 = null;
    box.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; }, { passive: true });
    box.addEventListener("touchend", function (e) {
      if (x0 === null) return;
      var dx = e.changedTouches[0].clientX - x0;
      x0 = null;
      if (Math.abs(dx) > 50) show(idx + (dx < 0 ? 1 : -1));
    }, { passive: true });
    box.addEventListener("close", function () { img.src = ""; });
  }

  /* --- kontaktný formulár --- */
  var form = d.querySelector("form.form");
  if (form) {
    var q = new URLSearchParams(location.search);
    var tema = q.get("tema") || (location.hash === "#kontakt" && q.get("t")) || "";
    var sel = form.querySelector("select[name='tema']");
    if (sel && tema) sel.value = tema;
    d.querySelectorAll("a[data-tema]").forEach(function (a) {
      a.addEventListener("click", function () { if (sel) sel.value = a.getAttribute("data-tema"); });
    });
    var stamp = form.querySelector("input[name='cas']");
    if (stamp) stamp.value = String(Date.now());

    var msg = form.querySelector(".form-msg");
    var btn = form.querySelector("button[type='submit']");
    var T = form.getAttribute("data-texts") ? JSON.parse(form.getAttribute("data-texts")) : {};

    function dopyt() {
      var fd = new FormData(form);
      var lines = [];
      form.querySelectorAll("[data-label]").forEach(function (el) {
        var v = el.tagName === "SELECT" ? el.options[el.selectedIndex].text : fd.get(el.name); // téma celým názvom
        if (v) lines.push(el.getAttribute("data-label") + ": " + v);
      });
      return { to: form.getAttribute("data-mail"), subject: T.subject || "Dopyt z webu noza.sk", body: lines.join("\n") };
    }

    // bez servera (GitHub Pages) alebo pri jeho výpadku ide dopyt e-mailom návštevníka: e-mailový program, a kto ho
    // nemá (pošta v prehliadači), má tlačidlá Gmail, Outlook a skopírovanie textu
    function cezEmail() {
      var m = dopyt(), k = encodeURIComponent;
      var odkaz = "mailto:" + m.to + "?subject=" + k(m.subject) + "&body=" + k(m.body);
      msg.innerHTML = (T.fallback || "")
        .replace(/\{link:([^}]*)\}/, '<a href="' + odkaz + '">$1</a>')
        .replace("{mail}", '<a href="mailto:' + m.to + '">' + m.to + "</a>");
      var tl = d.createElement("span");
      tl.className = "form-msg-btns";
      tl.innerHTML =
        '<a href="https://mail.google.com/mail/?view=cm&fs=1&to=' + k(m.to) + "&su=" + k(m.subject) + "&body=" + k(m.body) +
        '" target="_blank" rel="noopener">Gmail</a>' +
        '<a href="https://outlook.office.com/mail/deeplink/compose?to=' + k(m.to) + "&subject=" + k(m.subject) +
        "&body=" + k(m.body) + '" target="_blank" rel="noopener">Outlook</a>' +
        '<button type="button">' + (T.copy || "Kopírovať text") + "</button>";
      var kopia = tl.querySelector("button");
      kopia.addEventListener("click", function () {
        (navigator.clipboard ? navigator.clipboard.writeText(m.body) : Promise.reject())
          .then(function () { kopia.textContent = T.copied || "Skopírované"; })
          .catch(function () { window.prompt(T.copy || "Kopírovať text", m.body); });
      });
      msg.appendChild(tl);
      msg.className = "form-msg info";
      try { window.location.href = odkaz; } catch (e) { /* bez e-mailového programu ostávajú tlačidlá */ }
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!form.reportValidity()) return;
      msg.className = "form-msg";
      var endpoint = form.getAttribute("action");
      if (!endpoint) return cezEmail(); // statický hosting: PHP nebeží, dopyt hneď ide e-mailom (dáta nejdú na žiadny server)
      btn.disabled = true;
      fetch(endpoint, { method: "POST", body: new FormData(form), headers: { "Accept": "application/json" } })
        .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)); })
        .then(function (j) {
          if (!j || !j.ok) throw new Error("server");
          msg.textContent = T.ok;
          msg.className = "form-msg ok";
          form.reset();
          if (stamp) stamp.value = String(Date.now());
        })
        .catch(function () { cezEmail(); })
        .finally(function () { btn.disabled = false; });
    });
  }
})();
