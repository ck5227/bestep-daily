"""Render one day's BESTEP listening set into a 1080p practice video.

Usage: python make_video.py raw/sets/2026-10-31.json [out_dir]
Needs: edge_tts + Pillow (the kids_english_video venv has both) and ffmpeg on PATH.
Output: <out_dir>/bestep-<date>.mp4 and <out_dir>/bestep-<date>.txt (YouTube title/description).
"""
import asyncio, json, os, pathlib, subprocess, sys, wave
import edge_tts
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
SR = 24000
SITE = "https://ck5227.github.io/bestep-daily/"
VOICES = {"M": "en-US-AndrewNeural", "W": "en-US-JennyNeural", "N": "en-US-AvaNeural"}
C = dict(bg="#F4F6F9", paper="#FFFFFF", ink="#1C2633", muted="#5D6878", line="#D9E0EA",
         accent="#2C5AA0", soft="#E6EDF8", hl="#F5D35C", ok="#1F7A4D", oksoft="#E3F3EA")
FONT = os.environ.get("BESTEP_FONT") or "C:/Windows/Fonts/msjh.ttc"
FONT_B = os.environ.get("BESTEP_FONT_BOLD") or "C:/Windows/Fonts/msjhbd.ttc"
LP = {1: "Part 1 問答", 2: "Part 2 短篇言談", 3: "Part 3 長篇言談"}
LETTERS = "ABCDEF"
NUM = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
       "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
       "nineteen", "twenty"]


def num(n):
    """English words for 1-99, so TTS reads question numbers naturally."""
    if n < len(NUM):
        return NUM[n]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"][n // 10]
    return tens + ("-" + NUM[n % 10] if n % 10 else "")


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def tokens(text):
    """Split into wrap units: latin words keep their trailing space, CJK breaks per character."""
    out, buf = [], ""
    for ch in text:
        if ord(ch) > 0x2E80:
            if buf:
                out.append(buf); buf = ""
            out.append(ch)
        else:
            buf += ch
            if ch == " ":
                out.append(buf); buf = ""
    if buf:
        out.append(buf)
    return out


def wrap(text, f, width):
    lines, cur = [], ""
    for t in tokens(text):
        if cur and f.getlength(cur + t) > width:
            lines.append(cur.rstrip()); cur = t.lstrip()
        else:
            cur += t
    if cur.strip():
        lines.append(cur.rstrip())
    return lines or [""]


class Card:
    def __init__(self, s, header):
        self.img = Image.new("RGB", (W, H), C["bg"])
        self.d = ImageDraw.Draw(self.img)
        d = self.d
        d.rectangle([0, 0, W, 96], fill=C["ink"])
        d.text((80, 48), "BESTEP 校園英文每日練", font=font(34, True), fill="#FFFFFF", anchor="lm")
        d.text((W - 80, 48), f"{s['date']} · {s.get('theme', '')}", font=font(30), fill="#C9D3E0", anchor="rm")
        if header:
            d.text((80, 150), header, font=font(40, True), fill=C["accent"], anchor="lm")
        d.text((W - 80, H - 40), SITE, font=font(26), fill=C["muted"], anchor="rm")

    def save(self, path):
        self.img.save(path)


def layout_block(rows, size, width):
    """rows: list of (kind, text, meta). Returns (total_height, laid-out lines) for a font size."""
    laid, y = [], 0
    for kind, text, meta in rows:
        if kind == "q":
            f = font(size, True); ls = wrap(text, f, width); lh = int(size * 1.35)
            laid.append((kind, ls, meta, f, lh, y)); y += lh * len(ls) + int(size * 0.35)
        elif kind == "opt":
            f = font(size); ls = wrap(text, f, width - int(size * 2.2)); lh = int(size * 1.35)
            laid.append((kind, ls, meta, f, lh, y)); y += lh * len(ls) + int(size * 0.45)
        elif kind == "explain":
            f = font(int(size * 0.9)); ls = wrap(text, f, width - 60); lh = int(size * 1.4)
            y += int(size * 0.4)
            laid.append((kind, ls, meta, f, lh, y)); y += lh * len(ls) + 50
        elif kind == "gap":
            y += int(size * 0.7)
    return y, laid


def draw_block(card, rows, top=210, bottom=H - 90, left=110, width=W - 220):
    size = 44
    while size > 24:
        h, laid = layout_block(rows, size, width)
        if h <= bottom - top:
            break
        size -= 2
    h, laid = layout_block(rows, size, width)
    y0 = top + max(0, (bottom - top - h) // 2)
    d = card.d
    for kind, ls, meta, f, lh, y in laid:
        y += y0
        if kind == "q":
            for i, l in enumerate(ls):
                d.text((left, y + i * lh), l, font=f, fill=C["ink"])
        elif kind == "opt":
            state = meta.get("state")
            r = int(size * 0.62); cx = left + r; cy = y + lh // 2
            if state == "right":
                d.rounded_rectangle([left - 16, y - 8, left + width, y + lh * len(ls) + 4], 12, fill=C["oksoft"], outline=C["ok"], width=3)
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=C["ok"])
                bub = "#FFFFFF"
            else:
                d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=C["muted"], width=3)
                bub = C["muted"]
            d.text((cx, cy), meta["letter"], font=font(int(size * 0.7), True), fill=bub, anchor="mm")
            col = C["ink"] if state != "dim" else C["muted"]
            for i, l in enumerate(ls):
                d.text((left + int(size * 2.2), y + i * lh), l, font=f, fill=col)
        elif kind == "explain":
            d.rounded_rectangle([left - 16, y - 20, left + width, y + lh * len(ls) + 10], 12, fill=C["paper"], outline=C["line"], width=2)
            for i, l in enumerate(ls):
                d.text((left + 20, y + i * lh), l, font=f, fill=C["ink"])


# ---------- audio ----------
async def tts(text, voice, path, rate="+0%"):
    await edge_tts.Communicate(text, voice, rate=rate).save(str(path))


def to_frames(mp3):
    wav = mp3.with_suffix(".wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-ac", "1", "-ar", str(SR), str(wav)], check=True)
    with wave.open(str(wav)) as w:
        return w.readframes(w.getnframes())


def silence(sec):
    return b"\x00\x00" * int(SR * sec)


class Audio:
    def __init__(self, tmp):
        self.tmp, self.n = tmp, 0

    def say(self, text, voice="N", rate="+0%"):
        self.n += 1
        p = self.tmp / f"tts{self.n:04d}.mp3"
        for attempt in range(8):
            try:
                asyncio.run(tts(text, VOICES.get(voice, VOICES["N"]), p, rate)); break
            except Exception:
                if attempt == 7:
                    raise
                __import__("time").sleep(3 * (attempt + 1))  # edge-tts drops requests intermittently
        return to_frames(p)


# ---------- assembly ----------
def segment(tmp, idx, img_path, pcm):
    wav = tmp / f"seg{idx:03d}.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm)
    mp4 = tmp / f"seg{idx:03d}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(img_path), "-i", str(wav),
                    "-c:v", "libx264", "-tune", "stillimage", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", "30",
                    "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k", "-shortest", str(mp4)], check=True)
    return mp4


def main(src, out_dir):
    s = json.loads(pathlib.Path(src).read_text(encoding="utf-8"))
    out_dir = pathlib.Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    mock = s.get("type") == "mock"
    slug = f"bestep-mock-{s['date']}" if mock else f"bestep-{s['date']}"
    tmp = out_dir / f"tmp-{slug}"; tmp.mkdir(exist_ok=True)
    au = Audio(tmp)
    segs = []

    def add(card, pcm):
        p = tmp / f"img{len(segs):03d}.png"; card.save(p)
        segs.append(segment(tmp, len(segs), p, pcm))

    # intro
    c = Card(s, None)
    d = c.d
    d.text((W // 2, 360), "BESTEP 聽力全真模擬考" if mock else "BESTEP 每日校園英文聽力", font=font(84, True), fill=C["ink"], anchor="mm")
    theme = s.get("theme", "")
    tf = font(64, True); tw = tf.getlength(theme)
    d.rectangle([W // 2 - tw / 2 - 10, 500, W // 2 + tw / 2 + 10, 548], fill=C["hl"])
    d.text((W // 2, 500), theme, font=tf, fill=C["ink"], anchor="mm")
    d.text((W // 2, 650), s["date"], font=font(48), fill=C["muted"], anchor="mm")
    d.text((W // 2, 760), "聽完題目後暫停作答，接著公布答案與中文詳解", font=font(38), fill=C["accent"], anchor="mm")
    if mock:
        d.text((W // 2, 840), "35 題 · Part 1 問答 12 題 · Part 2 短篇言談 11 題 · Part 3 長篇言談 12 題", font=font(34), fill=C["muted"], anchor="mm")
    welcome = ("This is the BESTEP listening mock test. There are thirty-five questions in three parts."
               if mock else "Welcome to BESTEP campus English daily listening practice.")
    add(c, silence(0.5) + au.say(welcome) + silence(1.2))

    n = 0
    for g in s.get("listening", []):
        qs = g.get("questions", [])
        first = n + 1; n += len(qs)
        label = f"第 {first} 題" if len(qs) == 1 else f"第 {first}–{n} 題"
        header = f"{LP.get(g['part'], 'Part ' + str(g['part']))} · {label}"
        per_q = []
        for k, q in enumerate(qs):
            rows = []
            if q.get("prompt"):
                rows.append(("q", f"{first + k}. {q['prompt']}", {}))
            elif len(qs) > 1 or g["part"] != 1:
                rows.append(("q", f"{first + k}.", {}))
            for i, o in enumerate(q["options"]):
                rows.append(("opt", o.replace("**", ""), {"letter": LETTERS[i]}))
            rows.append(("gap", "", {}))
            per_q.append(rows)
        if g["part"] == 1:
            per_q[0].insert(0, ("q", "請選出最適當的回應", {}))

        # question card + listening audio (Part 1 plays twice, like the real exam)
        c = Card(s, header)
        if len(per_q) >= 3:  # long talks: two columns so the text stays readable
            half = (len(per_q) + 1) // 2
            colw = (W - 220 - 80) // 2
            draw_block(c, sum(per_q[:half], []), left=110, width=colw)
            draw_block(c, sum(per_q[half:], []), left=110 + colw + 80, width=colw)
        else:
            draw_block(c, sum(per_q, []))
        intro = f"Question {num(first)}." if len(qs) == 1 else f"Questions {num(first)} to {num(n)}."
        pcm = au.say(intro) + silence(0.8)
        lines = b"".join(au.say(ln["t"], ln.get("s", "N")) + silence(0.45) for ln in g.get("audio", []))
        pcm += lines + (silence(1.2) + lines if g["part"] == 1 else b"")
        pcm += silence(5 + 3 * len(qs))
        add(c, pcm)

        # answer card per question
        for k, q in enumerate(qs):
            arows = []
            if q.get("prompt"):
                arows.append(("q", f"{first + k}. {q['prompt']}", {}))
            for i, o in enumerate(q["options"]):
                arows.append(("opt", o.replace("**", ""), {"letter": LETTERS[i], "state": "right" if i in q["answer"] else "dim"}))
            ans = "、".join(LETTERS[i] for i in q["answer"])
            arows.append(("explain", f"正解 {ans}　{q.get('explain', '')}", {}))
            c = Card(s, f"{LP.get(g['part'], '')} · 第 {first + k} 題 解答")
            draw_block(c, arows)
            add(c, au.say(f"The answer is {ans.replace('、', ' and ')}.") + silence(min(14, 5 + len(q.get("explain", "")) / 12)))

    # vocabulary recap
    for w in s.get("words", [])[:8]:
        c = Card(s, "本回單字" if mock else "今日單字")
        d = c.d
        d.text((W // 2, 380), w["en"], font=font(110, True), fill=C["ink"], anchor="mm")
        d.text((W // 2, 500), f"{w.get('pos', '')}  {w.get('zh', '')}", font=font(56), fill=C["accent"], anchor="mm")
        ef = font(42)
        for i, l in enumerate(wrap(w.get("ex", ""), ef, W - 400)):
            d.text((W // 2, 640 + i * 60), l, font=ef, fill=C["muted"], anchor="mm")
        pcm = au.say(w["en"], rate="-10%") + silence(0.6)
        if w.get("ex"):
            pcm += au.say(w["ex"]) + silence(1.2)
        add(c, pcm)

    # outro
    c = Card(s, None)
    d = c.d
    page = SITE + ("mock/" if mock else "")
    d.text((W // 2, 380), "閱讀 35 題與線上計時作答" if mock else "完整閱讀題與互動作答", font=font(72, True), fill=C["ink"], anchor="mm")
    d.text((W // 2, 520), page, font=font(56, True), fill=C["accent"], anchor="mm")
    d.text((W // 2, 660), "每 3 天一回模擬考 · 每天一回每日練習" if mock else "每天早上更新 · 訂閱頻道每天練一回",
           font=font(44), fill=C["muted"], anchor="mm")
    add(c, au.say("This is the end of the listening test. Try the reading section on our website. Good luck!" if mock
                  else "Find the full reading section on our website. See you tomorrow!") + silence(2.5))

    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in segs), encoding="utf-8")
    out = out_dir / f"{slug}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", "-movflags", "+faststart", str(out)], check=True)

    words = "、".join(f"{w['en']} {w.get('zh', '')}" for w in s.get("words", []))
    if mock:
        title = f"BESTEP 聽力全真模擬考 35 題 {s['date']}｜附答案詳解"
        desc = (f"BESTEP 聽力全真模擬考｜{s['date']}\n"
                f"依官方題型：Part 1 問答（12 題）、Part 2 短篇言談（11 題）、Part 3 長篇言談（12 題，含 5 選 2 複選題），共 35 題。"
                "每題聽完暫停作答，接著公布答案與中文詳解。\n\n"
                f"閱讀 35 題＋線上計時作答：{page}\n每日練習：{SITE}\n\n"
                + (f"本回重要單字：{words}\n\n" if words else "") + "#BESTEP #英文聽力 #模擬考 #大學英文 #英檢")
    else:
        title = f"BESTEP 校園英文聽力每日練 {s['date']}｜{theme}"
        desc = (f"BESTEP 校園英文每日練｜{s['date']} 主題：{theme}\n"
                f"聽力 {n} 題（Part 1–3），聽完暫停作答，接著公布答案與中文詳解，最後複習今日單字。\n\n"
                f"互動作答＋閱讀題：{SITE}\n\n"
                f"今日單字：{words}\n\n#BESTEP #英文聽力 #大學英文 #英檢")
    (out_dir / f"{slug}.txt").write_text(json.dumps({"title": title[:100], "description": desc}, ensure_ascii=False, indent=1), encoding="utf-8")
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    print(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else pathlib.Path(__file__).parent / "videos")
