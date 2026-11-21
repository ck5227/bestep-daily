"""Check a mock exam JSON against MOCK_SPEC.md. Usage: python validate_mock.py raw/mocks/<date>.json"""
import collections, json, re, sys


def main(path):
    s = json.load(open(path, encoding="utf-8"))
    errs = []

    def err(msg):
        errs.append(msg)

    for k in ("type", "id", "date", "theme", "listening", "reading"):
        if k not in s:
            err(f"missing top-level field: {k}")
    if s.get("type") != "mock":
        err('type must be "mock"')
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(s.get("date", ""))):
        err("date must be YYYY-MM-DD")

    ids = collections.Counter()
    letters = collections.Counter()

    def questions(sec):
        out = []
        for g in s.get(sec, []):
            for q in g.get("questions", []):
                out.append((g, q))
        return out

    for sec in ("listening", "reading"):
        qs = questions(sec)
        if len(qs) != 35:
            err(f"{sec}: {len(qs)} questions, need 35")
        parts = collections.Counter(g["part"] for g, _ in qs)
        want = {1: 12, 2: 11, 3: 12} if sec == "listening" else {1: 12, 2: 10, 3: 13}
        if dict(parts) != want:
            err(f"{sec}: questions per part {dict(parts)}, need {want}")
        for g, q in qs:
            qid = q.get("id", "?")
            ids[qid] += 1
            opts, ans = q.get("options", []), q.get("answer", [])
            if not q.get("explain"):
                err(f"{qid}: missing explain")
            if not ans or any(not isinstance(i, int) or i < 0 or i >= len(opts) for i in ans) or len(set(ans)) != len(ans):
                err(f"{qid}: bad answer {ans} for {len(opts)} options")
            if len(ans) == 2 and len(opts) != 5:
                err(f"{qid}: choose-two needs 5 options")
            if len(ans) == 1:
                letters[ans[0]] += 1
            p = g["part"]
            if sec == "listening":
                if not g.get("audio") or any(not a.get("t") or a.get("s") not in ("M", "W", "N") for a in g["audio"]):
                    err(f"{qid}: bad audio lines")
                if p == 1 and (len(opts) != 3 or q.get("prompt")):
                    err(f"{qid}: Part 1 needs 3 options and empty prompt")
                if p == 2 and len(opts) not in (3, 4):
                    err(f"{qid}: Part 2 needs 3 or 4 options")
                if p == 3 and len(ans) == 1 and len(opts) != 4:
                    err(f"{qid}: Part 3 single answer needs 4 options")
            else:
                if p == 1 and ("______" not in q.get("prompt", "") or len(opts) != 4):
                    err(f"{qid}: vocabulary needs ______ blank and 4 options")
                if p >= 2 and not g.get("passage"):
                    err(f"{qid}: Part {p} group needs passage")
                if p >= 2 and len(ans) == 1 and len(opts) != 4:
                    err(f"{qid}: reading Part {p} needs 4 options")

    l2 = {len(q["options"]) for g, q in questions("listening") if g["part"] == 2}
    if l2 != {3, 4}:
        err(f"listening Part 2 must mix 3- and 4-option questions (got {sorted(l2)})")
    if sum(len(q["answer"]) == 2 for g, q in questions("listening") if g["part"] == 3) < 2:
        err("listening Part 3 needs at least 2 choose-two questions")
    if len([g for g in s.get("reading", []) if g.get("part") == 2]) != 5:
        err("reading Part 2 needs 5 passages")
    long_groups = [g for g in s.get("reading", []) if g.get("part") == 3]
    if len(long_groups) != 3:
        err("reading Part 3 needs 3 passages")
    tables = [g["table"] for g in long_groups if g.get("table")]
    if not tables:
        err("reading Part 3 needs at least one passage with a table")
    for t in tables:
        if not t.get("headers") or not t.get("rows") or any(len(r) != len(t["headers"]) for r in t["rows"]):
            err("table rows must match headers")
    for qid, n in ids.items():
        if n > 1:
            err(f"duplicate question id {qid}")
    total = sum(letters.values())
    for i in range(3):
        if total and letters[i] / total < 0.12:
            err(f"answer letter {'ABC'[i]} is too rare ({letters[i]}/{total}); spread answers out")

    if errs:
        print("INVALID")
        print("\n".join(errs))
        sys.exit(1)
    print(f"OK {s['id']}: 35 listening + 35 reading")


if __name__ == "__main__":
    main(sys.argv[1])
