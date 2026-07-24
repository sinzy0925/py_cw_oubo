from __future__ import annotations

from google import genai

from config import ApplicantProfile
from scraper import JobDetail


class GeminiClient:
    def __init__(self, api_key: str, model: str, applicant: ApplicantProfile) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.applicant = applicant

    def _build_prompt(self, job: JobDetail) -> str:
        return f"""クラウドワークスの仕事に応募するため、案件の安全性判定と応募文を作成してください。

【応募者情報】
{self.applicant.to_prompt_block()}

【出力形式（必ず守ること）】
application_text の先頭1行目に、必ず次のいずれか1つだけを書いてください。
- [正常] … 一般的な仕事で、条件・報酬ともに応募して問題なさそう
- [注意] … 詐欺ではないが、応募はおすすめしにくい案件（単価が低すぎる、報酬と作業量が見合わない、条件が曖昧、負担が大きいなど）
- [危険] … 詐欺・外部誘導・実態のない副業など、応募を避けるべき

2行目以降の構成:
- [危険] の場合: 判定理由のみを簡潔に書く（応募文は不要）
- [正常] の場合: 判定理由を1〜2行で書いたあと、空行を入れ、応募文を書く
- [注意] の場合: なぜおすすめしにくいかを1〜3行で明記し、「応募はおすすめしません」と書いたあと、空行を入れ、参考用の応募文を書く

【応募文の条件】
- 丁寧語で書く
- 応募文本体は500字以内
- 仕事の「応募必須事項」があれば、必ず回答を含める

【判定の目安】
- LINE・Telegram・外部サイトへの誘導、事前の高額支払い、実態のない高額稼げる系 → [危険]
- 時給換算で極端に低い（例: 時給500円未満）、報酬欄と詳細欄の金額矛盾、作業量に対して報酬が少なすぎる、IS業務なのにデータ入力扱いなど実態と乖離 → [注意]
- 条件が曖昧、拘束時間が長いのに月額が低い、スキルや経験を要求する割に単価が見合わない → [注意]
- 上記の問題がなく、一般的な業務内容で報酬も妥当な範囲 → [正常]

【仕事情報】
{job.full_content}
"""

    def generate_application(self, job: JobDetail) -> str:
        prompt = self._build_prompt(job)
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return response.text or ""
