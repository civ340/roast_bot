# 🐍 Tongue — 嗆辣 & 藉口生成器

一個整合 Telegram / LINE / Discord 的 AI 互動機器人，支援本地 Ollama 與雲端模型（OpenAI、Anthropic），透過管理後台即時切換設定。

---

## 功能

### 嗆辣機器人 🐍
用戶傳任何文字，AI 用嗆辣的口氣評論。可以反覆按「再毒一點」，從損友嘴臉一路升到蛇王終極一擊，共 5 級。

| 等級 | 風格 |
|------|------|
| 😏 Lv.1 | 損友輕嘲，不傷感情 |
| 😈 Lv.2 | 刻薄有理，反駁不了 |
| 🐍 Lv.3 | 精準戳痛點，字字帶刺 |
| ☠️ Lv.4 | 全力開炮，讓人啞口無言 |
| 👑 Lv.5 | 巔峰之作，又笑又想翻白眼 |
| 💥 核彈 | 傳說等級，永生難忘 |

### 藉口生成器 📋
描述你的情況，AI 幫你生成藉口。按「再誇一點」逐步升級，從合理可信到宇宙級離譜，共 6 級，無次數限制換情況。

| 等級 | 風格 |
|------|------|
| 📋 Lv.1 | 合理可信，像真人在解釋 |
| 🎭 Lv.2 | 誇張博同情，戲劇性拉滿 |
| 💣 Lv.3 | 離譜但超認真，一臉無辜 |
| 🌀 Lv.4 | 超展開，牽扯無辜第三者 |
| 🚀 Lv.5 | 宇宙級，扯到量子力學與命運 |
| 👑 Lv.6 | 傳說藉口，邏輯自洽離現實十萬八千里 |

---

## 架構

```
使用者（Telegram / LINE / Discord）
        │
        ▼
   FastAPI 後端 ──── PostgreSQL
        │
        ▼
   LLM Service（依設定切換）
   ├── Ollama（本地）
   ├── OpenAI
   └── Anthropic
```

| 服務 | 技術 | Port |
|------|------|------|
| 後端 API | FastAPI + asyncpg | 8000 |
| 前端管理介面 | React + Vite + TypeScript + Tailwind | 5173 |
| 資料庫 | PostgreSQL 16 | 5433 |
| Telegram Bot | python-telegram-bot | — |
| LINE Bot | linebot-sdk v3（webhook） | /webhook/line |
| Discord Bot | discord.py | — |

---

## 快速開始

### 1. 複製設定檔

```bash
cp .env.example .env
```

填入必要的值（詳見下方環境變數說明）。

### 2. 啟動服務

```bash
# 標準啟動（Telegram + LINE + 管理後台）
docker compose up -d --build

# 含 Discord Bot
docker compose --profile discord up -d --build
```

### 3. 若使用 Ollama，拉取模型

```bash
# Ollama 需在宿主機執行
ollama pull llama3
```

### 4. 開啟管理後台

瀏覽器開啟 `http://localhost:5173`，進入「⚙️ 設定」切換模型與平台。

---

## 環境變數

| 變數 | 必填 | 說明 |
|------|------|------|
| `POSTGRES_USER` | ✓ | 資料庫帳號 |
| `POSTGRES_PASSWORD` | ✓ | 資料庫密碼 |
| `POSTGRES_DB` | ✓ | 資料庫名稱 |
| `API_SECRET_KEY` | ✓ | 後端 secret |
| `TELEGRAM_BOT_TOKEN` | 使用 Telegram 時必填 | 從 @BotFather 取得 |
| `LINE_CHANNEL_SECRET` | 使用 LINE 時必填 | LINE Developers Console |
| `LINE_CHANNEL_ACCESS_TOKEN` | 使用 LINE 時必填 | LINE Developers Console |
| `DISCORD_BOT_TOKEN` | 使用 Discord 時必填 | Discord Developer Portal |

> LLM provider、model、API key 透過管理後台設定，不需要寫在 `.env`。

---

## 管理後台

`http://localhost:5173`

| 頁面 | 功能 |
|------|------|
| 📊 總覽 | 用戶數、對話場次、訊息數、解鎖核彈統計、嗆辣等級分布圖 |
| 💬 對話記錄 | 所有對話的完整訊息記錄，可依場次查看，顯示模式（嗆辣/藉口）與等級 |
| ⚙️ 設定 | 切換 LLM provider / 模型名稱 / API Key / 啟用平台開關 |

---

## 各平台使用方式

### Telegram
1. 傳 `/start` → 選擇「嗆我 🐍」或「幫我找藉口 📋」
2. 輸入內容 → 收到回應 + 按鈕
3. 按「再毒一點 / 再誇一點」升級，按「換個目標 / 換個情況」重來

### LINE
- 直接傳文字 → 嗆辣模式
- 以「藉口」開頭傳文字（例：`藉口我遲到了`）→ 藉口模式
- Quick Reply 按鈕繼續升級

### Discord
- `/roast <text>` — 嗆辣評論
- `/excuse <situation>` — 生成藉口
- 按鈕升級，支援多用戶同時使用

---

## LINE Webhook 設定

LINE Bot 需要對外可存取的 URL。本地開發可用 [ngrok](https://ngrok.com)：

```bash
ngrok http 8000
# 將 https://xxxx.ngrok.io/webhook/line 填入 LINE Developers > Webhook URL
```

---

## 資料庫 Schema

```
users         — 用戶基本資料
sessions      — 每次對話的 session（mode: roast | excuse）
messages      — 每條訊息記錄
app_settings  — 後台設定（provider、model、api key 等）
```

---

## 開發

> **Python 版本需求：>= 3.11, < 3.14**（`asyncpg`、`discord.py` 含 C extension，3.14 尚無穩定 wheel）

```bash
# 後端（本地）
cd backend
python -m venv .venv && .venv\Scripts\activate  # Windows
# source .venv/bin/activate                      # macOS / Linux
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端（本地）
cd frontend
npm install
npm run dev
```
