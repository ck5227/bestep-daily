# BESTEP 全真模擬考：題目檔格式

每份模擬考是一個 JSON 檔：`raw/mocks/<YYYY-MM-DD>.json`（日期 = 出題當天，台灣時間）。
寫完一定要跑 `python validate_mock.py raw/mocks/<date>.json`，通過才可發佈。

## 規格（對應 BESTEP 官方指南）

- 聽力 35 題（約 35 分鐘，滿分 140）
  - Part 1 問答：第 1–12 題。12 個題組，各 1 題，3 選 1，`prompt` 留空字串（題目只播放不印出）。
  - Part 2 短篇言談：第 13–23 題。11 個題組，各 1 題，3 選 1 或 4 選 1（兩種都要出現）。
  - Part 3 長篇言談：第 24–35 題。4 段談話，各 3 題，4 選 1；其中至少 2 題是 5 選 2 複選題（5 個選項，`answer` 有 2 個索引，`prompt` 寫明 "(Choose TWO.)"）。
- 閱讀 35 題（約 50 分鐘，滿分 140）
  - Part 1 詞彙：第 1–12 題。12 個題組，各 1 題，4 選 1，`prompt` 句中空格寫成 `______`。
  - Part 2 短文閱讀：第 13–22 題。5 篇短文（公告、Email、簡訊、表單等），各 2 題，4 選 1。
  - Part 3 長文閱讀：第 23–35 題。3 篇長文，題數 4 + 4 + 5；其中至少 1 篇是「圖文整合」，必須帶 `table`（課表、價目、統計等），且至少 1 題要同時用到表格與文章才能答。

## 內容要求

- 全部是大學校園情境（課務、宿舍、社團、圖書館、實習、交換、行政公告、學術講座等），主題混合，不要和前幾份重複。
- 難度約 CEFR B1–B2，干擾選項要有道理（同音字、重複關鍵字、時間地點錯置），不能一眼看穿。
- 每題 `explain` 用繁體中文，說明正解依據並點出主要干擾選項為什麼錯。
- 聽力 `audio` 的每句 `t` 只寫要朗讀的英文；數字、時間、房號用英文念法寫出（例如 "three thirty", "room two oh five"），方便語音合成。說話者 `s`：`M` 男、`W` 女、`N` 旁白／廣播。
- `answer` 是 0 起算的選項索引陣列。各題正解位置要平均分散（A/B/C/D 都要常出現）。

## JSON 結構

```json
{
  "type": "mock",
  "id": "mock-2026-11-06",
  "date": "2026-11-06",
  "theme": "全真模擬考 第 1 回",
  "words": [ {"en": "deadline", "pos": "n.", "zh": "截止期限", "ex": "The deadline is Friday."} ],
  "listening": [
    {"id": "L1", "part": 1,
     "audio": [{"s": "W", "t": "Where can I pick up my student ID?"}],
     "questions": [{"id": "m1106-l01", "prompt": "", "options": ["...", "...", "..."], "answer": [2], "explain": "..."}]}
  ],
  "reading": [
    {"id": "R1", "part": 1,
     "questions": [{"id": "m1106-r01", "prompt": "Please ______ the form by Friday.", "options": ["submit", "admit", "commit", "permit"], "answer": [0], "explain": "..."}]},
    {"id": "R6", "part": 2, "title": "Library Notice", "head": ["From: ...", "Subject: ..."],
     "passage": ["paragraph 1", "paragraph 2"], "questions": [ ... ]},
    {"id": "R13", "part": 3, "title": "...", "passage": ["..."],
     "table": {"caption": "Shuttle bus timetable", "headers": ["Stop", "First bus", "Last bus"], "rows": [["Main Gate", "7:00", "22:30"]]},
     "questions": [ ... ]}
  ]
}
```

`words` 放 8–12 個本回重要單字。題目 `id` 全卷不可重複。`head`、`title`、`table` 可省略。
