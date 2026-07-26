# py_cw_oubo

クラウドワークスの新着求人を自動で収集し、Gemini API で応募文を生成する Python ツールです。

## 何のためのものか

クラウドワークスには毎日多くの求人が掲載されますが、一件ずつ内容を確認し、怪しい案件を見極め、応募文を書くのは時間がかかります。

このツールは、その作業を半自動化するために作られています。

1. **一覧ページから「新着」求人だけを取得**（PR 案件は除外）
2. **各求人の募集内容を取得**
3. **Gemini API で安全性判定と応募文を生成**
4. **結果を JSON で保存**

`.env` に応募者情報（名前・年齢・スキルなど）を書いておけば、誰でも自分用の応募文を生成できます。クラウドワークスへの自動応募は行いません。生成した応募文を確認して、手動で応募してください。

## 主な機能

- Playwright によるブラウザスクレイピング（JavaScript 生成ページに対応）
- 案件判定ラベル: `[正常]` / `[注意]` / `[危険]`
- 作業済み ID の管理（`output/processed_ids.txt`）
- 失敗 URL の再実行（`--retry-failed` / `--urls`）
- 既存 JSON のアーカイブ（`archive_output.py`）

## 必要環境

- Python 3.12 以上（推奨）
- Google Gemini API キー

## セットアップ

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\playwright install chromium
copy .env.example .env
```

`.env` を編集し、`GOOGLE_API_KEY` と応募者情報を設定してください。

## 使い方

### 通常実行（一覧ページから新着求人を処理）

```powershell
.venv\Scripts\python main.py
```

### 失敗分のみ再実行

```powershell
.venv\Scripts\python main.py --retry-failed
```

### 特定 URL のみ実行

```powershell
.venv\Scripts\python main.py --urls https://crowdworks.jp/public/jobs/13331682
```

### 既存 JSON を日時フォルダへ退避してから実行

```powershell
.venv\Scripts\python archive_output.py
.venv\Scripts\python main.py
```

または、まとめて実行:

```powershell
.\run_get_cw.ps1
```

## 出力ファイル

| ファイル | 説明 |
|----------|------|
| `output/{job_id}.json` | 応募文・判定結果などの詳細 |
| `output/processed_ids.txt` | 作業済み求人 ID（1行1件） |
| `output/failed_urls.txt` | 失敗した URL 一覧 |
| `output/YYYYMMDD_HHMMSS/*.json` | アーカイブ済み JSON |

### JSON の例

```json
{
  "job_id": "13331682",
  "url": "https://crowdworks.jp/public/jobs/13331682",
  "title": "PDFを見ながらExcelに文字入力するお仕事です",
  "status": "success",
  "application_text": "[注意]\n単価が低すぎるため応募はおすすめしません。\n\nはじめまして。...",
  "processed_at": "2026-07-24T10:30:47+00:00",
  "error": null
}
```

## 判定ラベル

| ラベル | 意味 |
|--------|------|
| `[正常]` | 条件・報酬ともに問題なさそう |
| `[注意]` | 詐欺ではないが、単価が低い・条件が曖昧などおすすめしにくい |
| `[危険]` | 詐欺・外部誘導など、応募を避けるべき |

## 作業済み ID について

- スキップ判定は `output/processed_ids.txt` を参照します
- 成功時に ID が自動追記されます
- 再実行したい場合は、該当 ID を `processed_ids.txt` から削除してください

新規分の JSON だけを `output/` に残したい場合:

```powershell
Remove-Item output\*.json
.venv\Scripts\python main.py
```

`processed_ids.txt` は削除しないでください。

## プロジェクト構成

```
py_cw_oubo/
├── main.py              # メイン処理
├── archive_output.py    # JSON アーカイブ
├── scraper.py           # Playwright スクレイピング
├── gemini_client.py     # Gemini API 呼び出し
├── processed_store.py   # 作業済み ID 管理
├── config.py            # 設定読み込み
├── .env.example         # 環境変数テンプレート
└── output/              # 出力先
```

## 注意事項

- クラウドワークスの利用規約・robots.txt を確認し、自己責任でご利用ください
- Gemini の判定は参考情報です。最終的な応募判断は自分で行ってください
- スクレイピングの間隔は各ページ 1 秒待機 + リクエスト間 2 秒です

## License

MIT License

Copyright (c) 2026 sinzy

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
