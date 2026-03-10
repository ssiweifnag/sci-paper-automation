# SCI Paper Automation MVP

一個面向 SCI 論文研究工作流的 MVP 專案骨架。

## MVP 範圍

目前版本先實作這些核心能力：

1. 文獻來源設定與標準化資料模型
2. LLM 客戶端抽象層（先提供 mock 與 Claude 預留介面）
3. 論文修訂代理骨架
4. 格式檢查器（章節、引用、圖表標號）
5. 期刊匹配 stub
6. 學術風險初篩 stub
7. Pipeline orchestration 與專案狀態管理

## 專案結構

```text
sci-paper-automation/
  config/
    project.example.yaml
    project.example.json
  prompts/
    revise_section.txt
    enhance_abstract.txt
    journal_match.txt
    integrity_review.txt
  src/sci_paper_automation/
    agents/
    clients/
    models/
    pipeline/
    utils/
  tests/
  README.md
  requirements.txt
```

## 快速開始

```bash
cd sci-paper-automation
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m sci_paper_automation.pipeline.main --config config/project.example.json
```

## 設計原則

- **API 優先合法來源**：Semantic Scholar、PubMed、OpenAlex、CrossRef、arXiv
- **LLM 與資料層分離**：避免 prompt 與商業 API 綁死
- **人工審核節點**：高風險輸出只做建議，不自動放行
- **可追溯**：所有輸出可存回 reports/、drafts/、literature/
- **先可跑，再變強**：MVP 先做穩定骨架，不追求一步到位

## 後續擴充方向

- Zotero 整合
- DOCX round-trip 編修
- 審稿意見回覆生成
- Box / Obsidian 整合
- journal metadata 真實資料源接入
- pre-submission checklist
