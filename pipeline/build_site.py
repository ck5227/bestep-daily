"""Build the static GitHub Pages copy of the BESTEP daily page.

Input:  raw/index.html (page saved from the claude.ai artifact)
        raw/sets/*.json (one daily set per file, exported from the artifact db)
Output: site/index.html, site/data/<date>.json, site/data/index.json
"""
import html as html_lib, json, os, pathlib, re

ROOT = pathlib.Path(__file__).parent
# Override with BESTEP_RAW / BESTEP_SITE when running from the repo copy (pipeline/) in the cloud.
RAW = pathlib.Path(os.environ.get("BESTEP_RAW") or ROOT / "raw")
SITE = pathlib.Path(os.environ.get("BESTEP_SITE") or ROOT / "site")
DATA = SITE / "data"
YOUTUBE = "https://www.youtube.com/channel/UCtvxiHqiSLNGb_bi3grRGzw"

LOADER = """  // ---------- data ----------
  (async () => {
    try{
      const idx = await fetch("data/index.json", {cache:"no-cache"}).then(r => r.json());
      const dates = (idx.dates||[]).slice(0, 60);
      sets = (await Promise.all(dates.map(d => fetch(`data/${d}.json`).then(r => r.ok ? r.json() : null).catch(() => null)))).filter(s => s && s.date);
    }catch(e){ showEmpty("題庫暫時無法連線","請稍後重新整理頁面。"); return; }
    if (!sets.length){ showEmpty("今天的題目還在準備中","每天早上 7:00（台灣時間）會自動加入一組新的校園英文聽讀題。"); return; }
    current = sets[0]; load(); render();
  })();
})();
</script>"""


BASE = "https://ck5227.github.io/bestep-daily/"
DESC = "BESTEP 校園英文每日練：每天早上更新一組大學校園情境的英文聽力、閱讀與單字練習題，附答案與中文詳解，可線上作答並朗讀聽力。"
LETTERS = "ABCDEF"


def esc(s):
    return html_lib.escape(str(s or ""), quote=True)


def strip_md(s):
    # drop **bold** / __underline__ markers but keep ______ fill-in blanks
    return re.sub(r"__([^_]+?)__", r"\1", re.sub(r"\*\*(.+?)\*\*", r"\1", str(s or "")))


def seo_head(title, desc, url, extra=""):
    return f"""<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="zh_TW">
<meta name="google-site-verification" content="QL6IUxthkmW3SRObyW_j_kFxUGekKRU4Z3BiklohCIM">
{extra}"""


def table_html(t):
    return ('<table class="tbl">' + (f"<caption>{esc(t.get('caption'))}</caption>" if t.get("caption") else "")
            + "<tr>" + "".join(f"<th>{esc(h)}</th>" for h in t["headers"]) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in t["rows"]) + "</table>")


def day_page(s, mock=False):
    """Static, crawlable page for one set (questions shown, answers folded)."""
    url = f"{BASE}{'mock' if mock else 'day'}/{s['date']}.html"
    theme = s.get("theme", "")
    name = "BESTEP 全真模擬考" if mock else "BESTEP 校園英文練習"
    home = "./" if mock else "../"
    title = f"{name} {s['date']}｜{theme}"
    words = s.get("words", [])
    if mock:
        desc = f"{s['date']} BESTEP 全真模擬考：聽力 35 題、閱讀 35 題，依官方題型（問答、短篇／長篇言談、詞彙、短文、長文與圖文整合），附答案與中文詳解。"
    else:
        desc = f"{s['date']} BESTEP 校園英文練習，主題「{theme}」：閱讀題、聽力題與今日單字（" + "、".join(w["en"] for w in words[:6]) + "），附答案與中文詳解。"
    body = [f'<p class="crumb"><a href="{home}">← 線上作答（含聽力朗讀）</a></p>',
            f"<h1>{name} {s['date']}<br><span>{esc(theme)}</span></h1>"]

    def qblock(q, n):
        out = [f'<div class="q"><p><b>{n}.</b> {esc(strip_md(q.get("prompt"))) or "（請選出最適當的回應）"}</p><ol type="A">']
        out += [f"<li>{esc(strip_md(o))}</li>" for o in q["options"]]
        ans = "、".join(LETTERS[i] for i in q["answer"])
        out.append(f'</ol><details><summary>看答案與詳解</summary><p>正解 <b>{ans}</b>　{esc(strip_md(q.get("explain")))}</p></details></div>')
        return "".join(out)

    body.append("<h2>今日單字</h2><dl>")
    for w in words:
        body.append(f"<dt>{esc(w['en'])} <i>{esc(w.get('pos'))}</i> {esc(w.get('zh'))}</dt><dd>{esc(w.get('ex'))}</dd>")
    body.append("</dl><h2>閱讀 Reading</h2>")
    n = 0
    for g in s.get("reading", []):
        if g.get("passage"):
            body.append('<div class="passage">' + (f"<h3>{esc(g.get('title'))}</h3>" if g.get("title") else "")
                        + "".join(f"<p>{esc(h)}</p>" for h in g.get("head", []))
                        + "".join(f"<p>{esc(strip_md(p))}</p>" for p in g["passage"])
                        + (table_html(g["table"]) if g.get("table") else "") + "</div>")
        for q in g.get("questions", []):
            n += 1; body.append(qblock(q, n))
    body.append(f"<h2>聽力 Listening</h2><p>聽力音檔請到<a href=\"{home}\">線上作答頁</a>播放；以下為題目選項，聽力原文在詳解中。</p>")
    n = 0
    for g in s.get("listening", []):
        for q in g.get("questions", []):
            n += 1; body.append(qblock(q, n))
        script = " ".join(l["t"] for l in g.get("audio", []))
        body.append(f'<details><summary>聽力原文</summary><p>{esc(script)}</p></details>')
    body.append(f'<p class="crumb"><a href="{home}">← 回到{name}</a>　<a href="{YOUTUBE}">YouTube 聽力影片</a></p>')

    ld = {"@context": "https://schema.org", "@type": "LearningResource", "name": title, "description": desc,
          "url": url, "inLanguage": ["en", "zh-TW"], "datePublished": s["date"], "educationalLevel": "University",
          "learningResourceType": "Practice quiz", "about": "BESTEP English test"}
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{seo_head(title, desc, url, '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script>')}
<style>:root{{--bg:#F4F6F9;--ink:#1C2633;--muted:#5D6878;--accent:#2C5AA0;--line:#D9E0EA;--paper:#fff}}
@media (prefers-color-scheme:dark){{:root{{--bg:#11161D;--ink:#E5EAF1;--muted:#9AA6B6;--accent:#86A9E6;--line:#2B3542;--paper:#18202A}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 system-ui,"Noto Sans TC",sans-serif}}
main{{max-width:760px;margin:0 auto;padding:24px 16px 60px}} a{{color:var(--accent)}} h1 span{{font-size:.8em;color:var(--accent)}}
h2{{border-top:2px solid var(--ink);padding-top:10px;margin-top:36px}} dt{{font-weight:600;margin-top:10px}} dd{{margin:0;color:var(--muted)}}
.passage,.q{{background:var(--paper);border:1px solid var(--line);border-radius:6px;padding:12px 16px;margin:12px 0}}
details summary{{cursor:pointer;color:var(--accent)}} .crumb{{font-size:14px}}
.tbl{{border-collapse:collapse;margin:8px 0;font-size:14px;display:block;overflow-x:auto}} .tbl caption{{text-align:left;font-weight:600;padding-bottom:4px}}
.tbl th,.tbl td{{border:1px solid var(--line);padding:4px 10px;text-align:left}} .tbl th{{background:var(--bg)}}</style></head>
<body><main>{''.join(body)}</main></body></html>"""


MOCK_DESC = "BESTEP 全真模擬考：每 3 天一回，聽力 35 題（約 35 分鐘）＋閱讀 35 題（約 50 分鐘），依官方題型出題，含計時、作答與中文詳解，分數換算為 140 分制。"
TABLE_JS = ('+ (g.table?`<table class="tbl">${g.table.caption?`<caption>${esc(g.table.caption)}</caption>`:""}'
            '<tr>${g.table.headers.map(h=>`<th>${esc(h)}</th>`).join("")}</tr>'
            '${g.table.rows.map(r=>`<tr>${r.map(c=>`<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</table>`:"");')
TABLE_CSS = ("<style>.tbl{border-collapse:collapse;margin:4px 0 8px;font-family:var(--f-ui);font-size:14px;display:block;overflow-x:auto}"
             ".tbl caption{text-align:left;font-weight:600;padding-bottom:4px}.tbl th,.tbl td{border:1px solid var(--line);padding:4px 10px;text-align:left}"
             ".tbl th{background:var(--bg)}</style>")
TIMER_JS = """<script>(function(){
  // per-section countdown for the mock test: runs only while that section's tab is open and not yet submitted
  const lim={listening:35*60,reading:50*60}, left={}, el=document.getElementById("timer");
  setInterval(()=>{
    const sec=document.querySelector('.tab[aria-selected="true"]')?.dataset.sec;
    if(!lim[sec]){ el.textContent=""; return; }
    const k=document.getElementById("dateLabel").textContent+"|"+sec;
    if(!(k in left)) left[k]=lim[sec];
    if(!document.getElementById("submit").hidden && left[k]>0) left[k]--;
    const m=Math.floor(left[k]/60), s=left[k]%60;
    el.textContent=`剩餘 ${m}:${String(s).padStart(2,"0")}`; el.style.color=left[k]?"":"var(--bad)";
  },1000);
})();</script>"""


def load_sets(folder, out_data, page_dir, mock):
    out_data.mkdir(parents=True, exist_ok=True); page_dir.mkdir(parents=True, exist_ok=True)
    dates, themes = [], {}
    # Sets already published in the site (out_data) plus raw ones; a raw file wins for the same name.
    files = {f.name: f for f in out_data.glob("2*.json")}
    files.update({f.name: f for f in folder.glob("*.json")} if folder.is_dir() else {})
    for f in [files[k] for k in sorted(files)]:
        d = json.loads(f.read_text(encoding="utf-8"))
        if not d.get("date"):
            continue
        d = {k: v for k, v in d.items() if not k.startswith("_")}
        (out_data / f"{d['date']}.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        (page_dir / f"{d['date']}.html").write_text(day_page(d, mock), encoding="utf-8")
        dates.append(d["date"]); themes[d["date"]] = d.get("theme", "")
    dates.sort(reverse=True)
    (out_data / "index.json").write_text(json.dumps({"dates": dates}), encoding="utf-8")
    return dates, themes


def finish(html):
    # the artifact page keeps <title>, fonts and styles at the top of <body>; Google only reads
    # verification/meta tags from <head>, so move everything before the page content up there
    head_end = html.index("</head>")
    body_start = html.index("<body>", head_end) + len("<body>")
    content = html.index('<div class="wrap">', body_start)
    html = html[:head_end] + html[body_start:content] + "</head><body>\n" + html[content:]
    if not html.lstrip().lower().startswith("<!doctype"):
        html = "<!doctype html>\n" + html
    return html.replace("<meta charset=utf8>", '<meta charset="utf-8">')


def footer(title, links, desc):
    return (f'\n  <footer style="margin-top:48px;border-top:1px solid var(--line);padding-top:16px;font-size:14px">'
            f'<h2 style="font-size:16px">{title}</h2><ul style="padding-left:20px;columns:2">{links}</ul>'
            f'<p style="color:var(--muted)">{esc(desc)}</p></footer>\n</div>\n\n<div class="bar"')


def main():
    dates, themes = load_sets(RAW / "sets", DATA, SITE / "day", False)
    mdates, mthemes = load_sets(RAW / "mocks", SITE / "mock" / "data", SITE / "mock", True)

    base = (RAW / "index.html").read_text(encoding="utf-8")
    base, n = re.subn(r"  // ---------- data ----------.*?</script>", lambda m: LOADER, base, flags=re.S)
    assert n == 1, "data loader block not found in raw/index.html"
    old = 'g.passage.map(p=>`<p>${md(p)}</p>`).join("");'
    assert old in base, "passage render line not found"
    base = base.replace(old, old[:-1] + TABLE_JS, 1).replace("<html>", '<html lang="zh-Hant">', 1)
    base = base.replace("</head>", TABLE_CSS + "</head>", 1)

    # daily practice page
    html = base.replace(
        "<span>聽力 · 閱讀 · 單字</span>",
        f'<span>聽力 · 閱讀 · 單字</span><a href="mock/" style="color:var(--accent);font-weight:600">📝 全真模擬考（35＋35 題）</a>'
        f'<a href="{YOUTUBE}" style="color:var(--accent)">▶ YouTube 每日聽力影片</a>')
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": "BESTEP 校園英文每日練", "url": BASE,
          "description": DESC, "inLanguage": ["zh-TW", "en"]}
    html = html.replace("<title>BESTEP 校園英文每日練</title>", seo_head(
        "BESTEP 校園英文每日練｜每日聽力・閱讀・單字練習題", DESC, BASE,
        '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + "</script>"), 1)
    archive = "".join(f'<li><a href="day/{x}.html">{x}　{esc(themes[x])}</a></li>' for x in dates)
    html = html.replace("\n</div>\n\n<div class=\"bar\"", footer("歷史題目（文字版）", archive, DESC), 1)
    (SITE / "index.html").write_text(finish(html), encoding="utf-8")

    # mock test page: same app, its own data folder (mock/data), storage keys, timer and 140-point estimate
    murl = BASE + "mock/"
    html = base.replace('"bestep:"', '"bestep-mock:"')
    for a, b in [
        ("BESTEP · Campus English · Daily Set", "BESTEP · Full Mock Test"),
        ("每日校園英文：", "全真模擬考："),
        ("`${current.date} 的題組 · 每天早上 7:00 更新`", "`${current.date} · 聽力 35 題約 35 分鐘 · 閱讀 35 題約 50 分鐘`"),
        ("每天早上 7:00（台灣時間）會自動加入一組新的校園英文聽讀題。", "每 3 天自動產生一回完整模擬考。"),
        ("$(\"score\").textContent = `${right} / ${qs.length}`;",
         "$(\"score\").textContent = `${right} / ${qs.length}　≈ ${Math.round(right/qs.length*140)} / 140`;"),
        ('<span class="count" id="count">', '<span class="count" id="timer"></span><span class="count" id="count">'),
        ("<span>聽力 · 閱讀 · 單字</span>",
         f'<span>聽力 35 · 閱讀 35 · 滿分各 140</span><a href="../" style="color:var(--accent)">← 每日練習</a>'
         f'<a href="{YOUTUBE}" style="color:var(--accent)">▶ YouTube</a>'),
    ]:
        assert a in html, f"mock patch anchor not found: {a[:40]}"
        html = html.replace(a, b)
    mld = {"@context": "https://schema.org", "@type": "Quiz", "name": "BESTEP 全真模擬考", "url": murl,
           "description": MOCK_DESC, "inLanguage": ["zh-TW", "en"], "educationalLevel": "University", "about": "BESTEP English test"}
    html = html.replace("<title>BESTEP 校園英文每日練</title>", seo_head(
        "BESTEP 全真模擬考｜聽力・閱讀各 35 題線上計時測驗", MOCK_DESC, murl,
        '<script type="application/ld+json">' + json.dumps(mld, ensure_ascii=False) + "</script>"), 1)
    marchive = "".join(f'<li><a href="{x}.html">{x}　{esc(mthemes[x])}</a></li>' for x in mdates)
    html = html.replace("\n</div>\n\n<div class=\"bar\"", footer("歷屆模擬考（文字版）", marchive, MOCK_DESC), 1)
    html = html.replace("</body>", TIMER_JS + "</body>") if "</body>" in html else html + TIMER_JS
    (SITE / "mock" / "index.html").write_text(finish(html), encoding="utf-8")

    urls = ([(BASE, dates[0] if dates else None), (murl, mdates[0] if mdates else None)]
            + [(f"{BASE}day/{x}.html", x) for x in dates] + [(f"{murl}{x}.html", x) for x in mdates])
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc>" + (f"<lastmod>{m}</lastmod>" if m else "") + "</url>\n" for u, m in urls)
        + "</urlset>\n", encoding="utf-8")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n", encoding="utf-8")
    (SITE / ".nojekyll").write_text("")
    print(f"site built: {len(dates)} sets, latest {dates[0] if dates else '-'}; {len(mdates)} mock tests")


if __name__ == "__main__":
    main()
