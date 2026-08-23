"""
Renders a books/BookN_*.html file from a build_pipeline/specs/BookN_*.json
spec. The HTML/CSS/JS shell (styles, topbar, nav, easy-read toggle, quiz
logic, read-aloud engine, service-worker registration) is identical across
every existing book — this reproduces that exact shell and slots in only
the per-book content (title, pages, art, text, quiz).

Usage:
    python build_pipeline/render.py specs/Book1_Maya_Marcus_FireStation.json
    python build_pipeline/render.py --all
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BOOKS_DIR = REPO_ROOT / "books"
SPECS_DIR = Path(__file__).resolve().parent / "specs"

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#5BA672">
<title>{title} | Little Sprout Stories</title>
<link rel="manifest" href="../manifest.json">
<style>
:root {{ --sprout:#5BA672; --sprout-dark:#3C7A52; --cream:#FBF6EC; --ink:#2b2b2b; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:'Comic Sans MS','Segoe UI',sans-serif; background:var(--cream); color:var(--ink); }}

body.easyread {{ font-family:'Verdana','Tahoma',sans-serif; letter-spacing:.045em; word-spacing:.16em; }}
body.easyread .text-a, body.easyread .text-b {{ line-height:1.95; }}

.topbar {{ max-width:640px; margin:0 auto; padding:10px 20px 0; display:flex; justify-content:flex-end; gap:8px; }}
.topbar button {{ background:#fff; border:2px solid var(--sprout); color:var(--sprout-dark); border-radius:20px;
  padding:6px 14px; font-size:14px; font-weight:bold; cursor:pointer; font-family:inherit; }}
.topbar button[aria-pressed="true"] {{ background:var(--sprout); color:#fff; }}

.page-wrap {{ max-width:640px; margin:0 auto; padding:12px 20px 20px; }}
.page {{ background:#fff; border-radius:20px; padding:24px; box-shadow:0 4px 16px rgba(0,0,0,0.1); }}
.cover {{ text-align:center; }}
.banner {{ background:var(--sprout); color:#fff; display:inline-block; padding:6px 18px; border-radius:20px; font-size:14px; margin-bottom:10px; }}
h1 {{ color:var(--sprout); font-size:28px; }}
.stage {{ position:relative; min-height:280px; border-radius:16px; margin:16px 0; display:flex; align-items:flex-end; justify-content:center; gap:10px; padding:16px; overflow:hidden; }}
/* BACKGROUND-SWAP: replace these gradients with real illustrated backgrounds when location art is supplied */
.backdrop-barbershop {{ background:linear-gradient(180deg,#e8f4dc 0%,#e8f4dc 50%,#a9d687 50%,#a9d687 100%); }}
.backdrop-garden {{ background:linear-gradient(180deg,#bfe3fa 0%,#bfe3fa 48%,#9fd37f 48%,#9fd37f 100%); }}
.backdrop-repair {{ background:linear-gradient(180deg,#f3ead6 0%,#f3ead6 52%,#d8c79e 52%,#d8c79e 100%); }}
.backdrop-street {{ background:linear-gradient(180deg,#bfe3ff 0%,#bfe3ff 55%,#c9c9c9 55%,#c9c9c9 100%); }}
.backdrop-firestation {{ background:linear-gradient(180deg,#ffd9a0 0%,#ffd9a0 45%,#e8433f 45%,#e8433f 100%); }}
.backdrop-police {{ background:linear-gradient(180deg,#d9eefb 0%,#d9eefb 52%,#8fc6ea 52%,#8fc6ea 100%); }}
.backdrop-library {{ background:linear-gradient(180deg,#f3ead6 0%,#f3ead6 50%,#c9b98e 50%,#c9b98e 100%); }}
.backdrop-doctor {{ background:linear-gradient(180deg,#fce0ee 0%,#fce0ee 52%,#eba9c9 52%,#eba9c9 100%); }}
.backdrop-center {{ background:linear-gradient(180deg,#fce0ee 0%,#fce0ee 50%,#e8b9d3 50%,#e8b9d3 100%); }}
.backdrop-school {{ background:linear-gradient(180deg,#fff1cc 0%,#fff1cc 50%,#f5d77e 50%,#f5d77e 100%); }}
.backdrop-bakery {{ background:linear-gradient(180deg,#ffe3cc 0%,#ffe3cc 52%,#f0b67f 52%,#f0b67f 100%); }}
.backdrop-postoffice {{ background:linear-gradient(180deg,#d9eefb 0%,#d9eefb 50%,#bfe3fa 50%,#bfe3fa 100%); }}
img.char {{ height:220px; object-fit:contain; }}

.hotspot {{ position:absolute; top:20px; font-size:40px; cursor:pointer; animation:bob 2s ease-in-out infinite;
  transition:transform .2s; background:none; border:none; padding:4px; line-height:1; }}
.hotspot.left {{ left:20px; }}
.hotspot.right {{ right:20px; }}
.hotspot.mid {{ left:50%; transform:translateX(-50%); }}
.hotspot.right2 {{ right:70px; top:44px; }}
@keyframes bob {{ 0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-8px)}} }}
@media (prefers-reduced-motion: reduce) {{ .hotspot {{ animation:none; }} }}

.helper-slot {{ font-size:60px; text-align:center; }}
.helper-label {{ font-size:14px; background:#fff; border-radius:8px; padding:2px 8px; }}

.readaloud {{ display:inline-flex; align-items:center; gap:8px; background:#fff; border:2px solid var(--sprout);
  color:var(--sprout-dark); border-radius:22px; padding:8px 16px; font-size:15px; font-weight:bold;
  cursor:pointer; margin-top:14px; font-family:inherit; }}
.readaloud:hover {{ background:#f2fbf5; }}
.readaloud.speaking {{ background:var(--sprout); color:#fff; }}
.readaloud[hidden] {{ display:none; }}

.text-a {{ font-size:18px; line-height:1.6; margin-top:12px; }}
.text-b {{ font-size:20px; font-weight:bold; background:#eaf7ee; border-left:5px solid var(--sprout); padding:10px 14px; border-radius:8px; margin-top:10px; }}
.w.spoken {{ background:#FFE9A3; border-radius:4px; }}

.quiz {{ margin-top:16px; background:#fff8e6; border-radius:12px; padding:14px; text-align:center; }}
.quiz-q {{ font-weight:bold; margin:0 0 8px; }}
.quiz button {{ display:block; width:100%; margin:6px 0; padding:12px; font-size:16px; border-radius:10px;
  border:2px solid var(--sprout); background:#fff; cursor:pointer; font-family:inherit; }}
.quiz button.correct {{ background:var(--sprout); color:#fff; }}
.quiz button.wrong {{ background:#C6453B; color:#fff; }}
.quiz-feedback {{ min-height:22px; font-weight:bold; color:var(--sprout-dark); margin:6px 0 0; }}

.start-btn {{ margin-top:20px; background:var(--sprout); color:#fff; border:none; padding:14px 28px; font-size:18px;
  border-radius:30px; cursor:pointer; font-family:inherit; display:inline-block; text-decoration:none; }}
.start-btn.ghost {{ background:#fff; color:var(--sprout-dark); border:2px solid var(--sprout); }}
.end-btns {{ display:flex; gap:10px; justify-content:center; flex-wrap:wrap; }}

.nav-row {{ max-width:640px; margin:0 auto; display:flex; justify-content:space-between; align-items:center; padding:0 20px 30px; gap:12px; }}
.nav-row button {{ background:var(--sprout); color:#fff; border:none; padding:12px 22px; border-radius:20px; font-size:16px; cursor:pointer; font-family:inherit; }}
.nav-row button:disabled {{ background:#ccc; cursor:default; }}
.progress {{ font-size:13px; color:#5c5c5c; }}

.end-screen {{ text-align:center; }}
.badge {{ font-size:60px; }}
.badge div {{ font-size:18px; font-weight:bold; color:var(--sprout); }}
.saved-note {{ font-size:14px; color:var(--sprout-dark); font-weight:bold; min-height:20px; }}
.guide {{ text-align:left; background:#eaf7ee; border-radius:12px; padding:16px; margin-top:16px; }}
.guide summary {{ font-weight:bold; cursor:pointer; font-size:17px; }}
.guide p {{ margin:10px 0 0; }}
.standards {{ font-size:12px; color:#666; }}

:focus-visible {{ outline:3px solid #185FA5; outline-offset:3px; border-radius:6px; }}
</style>
</head>
<body>

<div class="topbar">
  <button type="button" id="easyBtn" onclick="toggleEasy()" aria-pressed="false"
          title="Easier-to-read spacing">Aa</button>
</div>

<main id="bookMain">
"""

NAV_AND_SCRIPT = """</main>

<div class="nav-row">
  <button id="prevBtn" type="button" onclick="prevPage()" disabled>&#9664; Back</button>
  <span class="progress" id="progressLabel" aria-live="polite"></span>
  <button id="nextBtn" type="button" onclick="nextPage()">Next &#9654;</button>
</div>

<script>
const BOOK_ID = "{book_id}";
const BOOK_TITLE = "{book_title}";
const BOOK_BADGE = "{book_badge}";
let current = 0;
const total = {total};

/* ---------- progress: saved on this device only ---------- */
function loadProgress() {{
  try {{ return JSON.parse(localStorage.getItem('littlesprout') || '{{}}'); }}
  catch (e) {{ return {{}}; }}
}}
function saveProgress(data) {{
  try {{ localStorage.setItem('littlesprout', JSON.stringify(data)); return true; }}
  catch (e) {{ return false; }}
}}
function markFinished() {{
  const d = loadProgress();
  d.books = d.books || {{}};
  const already = d.books[BOOK_ID] && d.books[BOOK_ID].finished;
  d.books[BOOK_ID] = {{ finished:true, title:BOOK_TITLE, badge:BOOK_BADGE, at:Date.now() }};
  const ok = saveProgress(d);
  const note = document.getElementById('savedNote');
  if (note) note.textContent = ok
    ? (already ? 'Badge already in your collection!' : 'Badge saved to your collection!')
    : '';
}}

/* ---------- paging ---------- */
function show(i) {{
  stopSpeech();
  for (let j=0;j<total;j++) document.getElementById('p'+j).style.display = (j===i)?'block':'none';
  document.getElementById('prevBtn').disabled = (i===0);
  document.getElementById('nextBtn').style.display = (i===total-1)?'none':'inline-block';
  document.getElementById('progressLabel').textContent =
    (i===0) ? '' : (i===total-1 ? 'The end' : 'Page ' + i + ' of ' + (total-2));
  if (i===total-1) markFinished();
  window.scrollTo(0,0);
}}
function nextPage() {{ if (current<total-1) {{ current++; show(current); }} }}
function prevPage() {{ if (current>0) {{ current--; show(current); }} }}
function restart() {{ current = 0; show(0); }}

document.addEventListener('keydown', function(e) {{
  if (e.key === 'ArrowRight') nextPage();
  else if (e.key === 'ArrowLeft') prevPage();
  else if (e.key === 'Escape') stopSpeech();
}});

/* ---------- hotspots ---------- */
function pulse(el) {{ el.style.transform='scale(1.3)'; setTimeout(()=>{{el.style.transform='';}},200); }}
function ding(el) {{
  pulse(el);
  try {{
    const ctx = new (window.AudioContext||window.webkitAudioContext)();
    const o = ctx.createOscillator(); const g = ctx.createGain();
    o.connect(g); g.connect(ctx.destination);
    o.frequency.value = 880; g.gain.value = 0.12;
    o.start(); setTimeout(()=>o.stop(), 350);
  }} catch(e) {{}}
}}

/* ---------- quiz ---------- */
function checkAnswer(btn, chosen) {{
  const quiz = btn.closest('.quiz');
  const answer = parseInt(quiz.dataset.answer);
  const fb = quiz.querySelector('.quiz-feedback');
  const btns = [].slice.call(quiz.querySelectorAll('button'));
  btns.forEach(function(b,i) {{
    b.disabled = true;
    if (i===answer) b.classList.add('correct');
    else if (i===chosen) b.classList.add('wrong');
  }});
  if (fb) fb.textContent = (chosen===answer)
    ? 'That\\u2019s right!'
    : 'Good try \\u2014 the green one is the answer.';
}}

/* ---------- easy-read toggle ---------- */
function toggleEasy() {{
  const on = document.body.classList.toggle('easyread');
  document.getElementById('easyBtn').setAttribute('aria-pressed', on ? 'true':'false');
  const d = loadProgress(); d.easyread = on; saveProgress(d);
}}
(function initEasy() {{
  if (loadProgress().easyread) {{
    document.body.classList.add('easyread');
    document.getElementById('easyBtn').setAttribute('aria-pressed','true');
  }}
}})();

/* ---------- read aloud ---------- */
const SPEECH_OK = ('speechSynthesis' in window) && ('SpeechSynthesisUtterance' in window);
let activeBtn = null;

if (!SPEECH_OK) {{
  [].slice.call(document.querySelectorAll('.readaloud')).forEach(function(b) {{ b.hidden = true; }});
}}

function pickVoice() {{
  const vs = speechSynthesis.getVoices().filter(function(v) {{
    return v.lang && v.lang.toLowerCase().indexOf('en') === 0;
  }});
  if (!vs.length) return null;
  const preferred = ['Samantha','Google US English','Microsoft Aria','Microsoft Zira','Karen','Moira'];
  for (var i=0;i<preferred.length;i++) {{
    var hit = vs.find(function(v) {{ return v.name.indexOf(preferred[i]) !== -1; }});
    if (hit) return hit;
  }}
  return vs.find(function(v) {{ return v.localService; }}) || vs[0];
}}

function wrapWords(el) {{
  if (el.dataset.wrapped === '1') return;
  const text = el.textContent;
  el.innerHTML = text.split(/(\\s+)/).map(function(tok) {{
    if (tok === '' || /^\\s+$/.test(tok)) return tok;
    return '<span class="w">' + tok.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</span>';
  }}).join('');
  el.dataset.wrapped = '1';
}}

function stopSpeech() {{
  if (SPEECH_OK) {{ try {{ speechSynthesis.cancel(); }} catch(e) {{}} }}
  [].slice.call(document.querySelectorAll('.w.spoken')).forEach(function(s) {{ s.classList.remove('spoken'); }});
  if (activeBtn) {{
    activeBtn.classList.remove('speaking');
    var lbl = activeBtn.querySelector('.ra-label');
    if (lbl) lbl.textContent = 'Read to me';
    activeBtn = null;
  }}
}}

function readPage(btn) {{
  if (!SPEECH_OK) return;
  if (activeBtn === btn) {{ stopSpeech(); return; }}
  stopSpeech();

  const page = btn.closest('.page');
  const blocks = [page.querySelector('.text-a'), page.querySelector('.text-b')].filter(Boolean);
  blocks.forEach(wrapWords);

  activeBtn = btn;
  btn.classList.add('speaking');
  var lbl = btn.querySelector('.ra-label');
  if (lbl) lbl.textContent = 'Stop';

  var queue = blocks.slice();
  function speakBlock() {{
    if (!queue.length) {{ stopSpeech(); return; }}
    var el = queue.shift();
    var spans = [].slice.call(el.querySelectorAll('.w'));
    var plain = el.textContent;
    var offsets = []; var cursor = 0;
    spans.forEach(function(s) {{
      var idx = plain.indexOf(s.textContent, cursor);
      offsets.push(idx); cursor = idx + s.textContent.length;
    }});

    var u = new SpeechSynthesisUtterance(plain);
    var v = pickVoice(); if (v) u.voice = v;
    u.rate = 0.85; u.pitch = 1.05;
    u.onboundary = function(ev) {{
      if (ev.name && ev.name !== 'word') return;
      var hit = -1;
      for (var i=0;i<offsets.length;i++) {{ if (offsets[i] <= ev.charIndex) hit = i; else break; }}
      spans.forEach(function(s) {{ s.classList.remove('spoken'); }});
      if (hit >= 0 && spans[hit]) spans[hit].classList.add('spoken');
    }};
    u.onend = function() {{
      spans.forEach(function(s) {{ s.classList.remove('spoken'); }});
      if (activeBtn === btn) speakBlock();
    }};
    u.onerror = function() {{ stopSpeech(); }};
    speechSynthesis.speak(u);
  }}
  speakBlock();
}}

if (SPEECH_OK) {{ speechSynthesis.onvoiceschanged = function() {{}}; }}
window.addEventListener('beforeunload', stopSpeech);

if ('serviceWorker' in navigator) {{
  window.addEventListener('load', function() {{
    navigator.serviceWorker.register('../sw.js').catch(function() {{}});
  }});
}}

show(0);
</script>
</body>
</html>"""


def render_stage_element(el: dict) -> str:
    if el["type"] == "img":
        return f'<img class="char" src="../assets/sprites/{el["sprite"]}" alt="{el["alt"]}" loading="lazy">'
    if el["type"] == "helper":
        return (
            f'<div class="helper-slot" role="img" aria-label="{el["name"]}">{el["emoji"]}'
            f'<div class="helper-label">{el["name"]}</div></div>'
        )
    if el["type"] == "hotspot":
        return (
            f'<button class="hotspot {el["position"]}" onclick="{el["effect"]}(this)" '
            f'aria-label="{el["aria_label"]}" type="button">{el["emoji"]}</button>'
        )
    raise ValueError(f"unknown stage element type: {el['type']!r}")


def render_stage(stage: dict) -> str:
    inner = "\n    ".join(render_stage_element(el) for el in stage["elements"])
    return f'<div class="stage {stage["backdrop"]}">\n    {inner}\n  </div>'


def render_quiz(quiz: dict | None) -> str:
    if not quiz:
        return ""
    opts = "\n      ".join(
        f'<button type="button" onclick="checkAnswer(this,{i})">{opt}</button>'
        for i, opt in enumerate(quiz["options"])
    )
    return (
        f'<div class="quiz" data-answer="{quiz["answer"]}" role="group" aria-label="Question">\n'
        f'    <p class="quiz-q">{quiz["question"]}</p>\n'
        f'    <div class="quiz-opts">\n      {opts}\n    </div>\n'
        f'    <p class="quiz-feedback" role="status" aria-live="polite"></p>\n'
        f'  </div>'
    )


def render_page(page: dict) -> str:
    quiz_html = render_quiz(page.get("quiz"))
    quiz_block = f"\n  {quiz_html}" if quiz_html else ""
    return (
        f'<div class="page-wrap" id="p{page["index"]}" style="display:none">\n'
        f'<section class="page">\n'
        f'  {render_stage(page["stage"])}\n'
        f'  <button class="readaloud" type="button" onclick="readPage(this)" aria-label="Read this page out loud">\n'
        f'    <span class="ra-icon" aria-hidden="true">&#128266;</span><span class="ra-label">Read to me</span>\n'
        f'  </button>\n'
        f'  <div class="text-a">{page["text_a"]}</div>\n'
        f'  <div class="text-b">{page["text_b"]}</div>{quiz_block}\n'
        f'</section></div>\n'
    )


def render_cover(spec: dict) -> str:
    cover = spec["cover"]
    return (
        f'<div class="page-wrap" id="p0" style="display:block">\n'
        f'<section class="page cover">\n'
        f'  <div class="banner">Little Sprout Stories</div>\n'
        f'  <h1>{cover["h1_html"]}</h1>\n'
        f'  {render_stage(cover["stage"])}\n'
        f'  <button class="start-btn" type="button" onclick="nextPage()">Start Reading &#9654;</button>\n'
        f'</section></div>\n'
    )


def render_end(spec: dict, end_index: int) -> str:
    e = spec["end_screen"]
    return (
        f'<div class="page-wrap" id="p{end_index}" style="display:none">\n'
        f'<section class="page end-screen">\n'
        f'  <div class="badge"><span aria-hidden="true">{e["badge_emoji"]}</span><div>{e["badge_label_html"]}</div></div>\n'
        f'  <h2>Great reading!</h2>\n'
        f'  <p class="saved-note" id="savedNote"></p>\n'
        f'  <details class="guide">\n'
        f'    <summary>For Grown-Ups</summary>\n'
        f'    <p><b>Feeling/skill:</b> {e["feeling"]}</p>\n'
        f'    <p><b>Ask your child:</b> {e["ask"]}</p>\n'
        f'    <p><b>Try this:</b> {e["try_this"]}</p>\n'
        f'    <p class="standards">Standards: {e["standards"]}</p>\n'
        f'  </details>\n'
        f'  <div class="end-btns">\n'
        f'    <button class="start-btn" type="button" onclick="restart()">Read Again &#9654;</button>\n'
        f'    <a class="start-btn ghost" href="../index.html">&#8592; More books</a>\n'
        f'  </div>\n'
        f'</section></div>\n'
    )


def render_book(spec: dict) -> str:
    total = len(spec["pages"]) + 2  # cover + interior pages + end
    end_index = total - 1
    out = [HEAD.format(title=spec["title"])]
    out.append(render_cover(spec))
    for page in spec["pages"]:
        out.append(render_page(page))
    out.append(render_end(spec, end_index))
    out.append(NAV_AND_SCRIPT.format(
        book_id=spec["book_id"], book_title=spec["book_title"],
        book_badge=spec["book_badge"], total=total,
    ))
    return "".join(out)


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--all":
        targets = sorted(SPECS_DIR.glob("*.json"))
    elif len(sys.argv) == 2:
        targets = [Path(sys.argv[1])]
    else:
        print("Usage: python render.py <specs/BookN_....json> | --all")
        return 1

    for path in targets:
        spec = json.loads(path.read_text(encoding="utf-8"))
        html = render_book(spec)
        out_path = BOOKS_DIR / (path.stem + ".html")
        out_path.write_text(html, encoding="utf-8", newline="\n")
        print(f"{path.name} -> {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
