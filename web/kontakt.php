<?php
/*
 * Kontaktný formulár NOZA — prijme POST z formulára a pošle e-mail.
 * Funguje na akomkoľvek PHP hostingu s mail(). Ostrý noza.sk je od 10/2026 na GitHub Pages, kde PHP nebeží.
 * Na statickom hostingu bez PHP (napr. Cloudflare Pages) tento súbor nebeží — formulár na webe
 * to spozná a ponúkne odoslanie cez vlastný e-mailový program (mailto).
 *
 * Nastavenie: zmeň $KOMU (adresa, kam chodia dopyty) a $OD (odosielateľ na doméne webu,
 * aby maily neskončili v spame — na hostingu musí existovať schránka alebo aspoň doména).
 * noza.sk má DMARC p=reject: obálkový odosielateľ (-f) musí byť na noza.sk a server webu musí byť
 * v SPF domény (Websupport: include:_spf.m1.websupport.sk), inak schránka príjemcu dopyt potichu odmietne.
 */
$KOMU = 'office@noza.sk';
$OD   = 'web@noza.sk';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function odpoved(bool $ok, string $sprava = ''): void {
    echo json_encode(['ok' => $ok, 'sprava' => $sprava], JSON_UNESCAPED_UNICODE);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    odpoved(false, 'Len POST.');
}

// poistky proti robotom: skryté pole musí byť prázdne, formulár musí byť otvorený aspoň 3 s
if (!empty($_POST['web'])) {
    odpoved(true); // robotovi tvárime úspech
}
$cas = (int)($_POST['cas'] ?? 0);
if ($cas > 0 && (round(microtime(true) * 1000) - $cas) < 3000) {
    odpoved(true);
}

$cisti = static function (string $k, int $max = 500): string {
    $v = trim((string)($_POST[$k] ?? ''));
    $v = str_replace(["\r", "\n"], ' ', $v);
    return mb_substr($v, 0, $max);
};

$meno    = $cisti('meno', 120);
$firma   = $cisti('firma', 160);
$email   = $cisti('email', 160);
$telefon = $cisti('telefon', 60);
$tema    = $cisti('tema', 20);
$jazyk   = $cisti('jazyk', 2) === 'de' ? 'de' : 'sk';
$sprava  = mb_substr(trim((string)($_POST['sprava'] ?? '')), 0, 5000);
$suhlas  = !empty($_POST['suhlas']);

if ($meno === '' || $sprava === '' || !$suhlas || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(422);
    odpoved(false, 'Chýbajú povinné údaje.');
}

$temy = ['prace' => 'Dopyt na montážne práce', 'partner' => 'Partnerská spolupráca', 'ine' => 'Iné'];
$temaText = $temy[$tema] ?? 'Iné';

$predmet = ($jazyk === 'de' ? 'Anfrage über noza.sk: ' : 'Dopyt z webu noza.sk: ') . $temaText . ' – ' . $meno;
$telo = "Nový dopyt z webu noza.sk (" . strtoupper($jazyk) . ")\n"
      . str_repeat('-', 40) . "\n"
      . "Meno:     $meno\n"
      . "Firma:    " . ($firma ?: '–') . "\n"
      . "E-mail:   $email\n"
      . "Telefón:  " . ($telefon ?: '–') . "\n"
      . "Téma:     $temaText\n"
      . "Čas:      " . date('d.m.Y H:i') . "\n"
      . "IP:       " . ($_SERVER['REMOTE_ADDR'] ?? '') . "\n"
      . str_repeat('-', 40) . "\n\n"
      . $sprava . "\n";

$hlavicky = "From: NOZA web <$OD>\r\n"
          . "Reply-To: =?UTF-8?B?" . base64_encode($meno) . "?= <$email>\r\n" // diakritika a čiarka v mene nerozbijú adresu
          . "MIME-Version: 1.0\r\n"
          . "Content-Type: text/plain; charset=UTF-8\r\n"
          . "Content-Transfer-Encoding: 8bit\r\n";

$predmetKod = '=?UTF-8?B?' . base64_encode($predmet) . '?=';
// obálka = existujúca schránka na noza.sk: zarovná SPF s DMARC a prípadné nedoručenie sa vráti tam, kde ho niekto uvidí
$poslane = @mail($KOMU, $predmetKod, $telo, $hlavicky, '-f' . $KOMU);

if (!$poslane) {
    http_response_code(500);
    odpoved(false, 'Server neodoslal e-mail.');
}
odpoved(true);
