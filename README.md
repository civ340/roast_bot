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

以下是**本機開發環境**的啟動方式。要對外部署（讓其他人能從網路連進來）請跳到
[對外部署](#對外部署) 那節，不要直接照抄這裡的指令。

### 1. 複製設定檔

```bash
cp .env.example .env
```

填入必要的值（詳見下方環境變數說明）。

**`API_SECRET_KEY` 一定要自己產生一組**，留空、用 `changeme` 或少於 16 個字元的話 backend 會拒絕啟動：

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. 啟動服務

**⚠️ 這裡的指令會經由 `docker-compose.override.yml` 把 backend 的 8000 port 發布到本機**
**（方便 `npm run dev` 的 vite proxy 跟 ngrok 測 LINE webhook）。對外部署時請改用
[對外部署](#對外部署) 那節的指令，否則 `/api/roast`、`/api/excuse` 這類內部端點會被公開存取。**

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

### 4. 建立管理後台帳號

後台需要登入才能存取，第一次使用需手動建立管理員帳號：

```bash
docker compose exec backend python create_admin.py
```

依照提示輸入帳號、密碼即可（密碼以 bcrypt 雜湊後存入 `admin_users` 資料表）。

### 5. 開啟管理後台

瀏覽器開啟 `http://localhost:5173`，用剛建立的帳號登入後進入「⚙️ 設定」切換模型與平台。

---

## 對外部署

要讓機器對外（非本機）可連線時，**不要**用「快速開始」裡的 `docker compose up -d --build`，
改用 `-f` 明確排除 `docker-compose.override.yml`，backend 的 8000 port 跟 postgres 的
5433 port 才都不會被公開：

```bash
docker compose -f docker-compose.yml up -d --build

# 含 Discord Bot
docker compose -f docker-compose.yml --profile discord up -d --build
```

這樣跑起來只有 `frontend`（nginx，5173）會發布到 host，其他服務都只透過 docker
內部網路互相溝通：

- `/api/roast`、`/api/excuse` 是給 Telegram/Discord bot 用的內部端點，靠
  `API_SECRET_KEY` 共享密鑰保護，不應該讓 backend 直接暴露在網路上。
  nginx 也會直接把從外面打進來的這兩個路徑回 404（bot 走 docker 內部網路，不經過 nginx）。
- postgres 也不該對外，不然資料庫密碼就變成唯一的防線。
- LINE 的 webhook（`/webhook/line`）改由 nginx 轉發給 backend（見
  `frontend/nginx.conf` 的 `location /webhook`），所以即使 backend 沒有對外，
  平台一樣可以打 `https://你的網域/webhook/line` 進來，不需要額外開 port。
- 這份 compose 沒有包含 HTTPS。對外服務時請在 nginx（5173）前面再放一層終結 TLS 的反向代理
  （Caddy、Cloudflare Tunnel 等），並確認它有帶 `X-Forwarded-Proto` 與 `X-Forwarded-For`：
  backend 靠前者幫登入 cookie 加上 `Secure`，nginx 靠後者取得真正的來源 IP（登入鎖定與頻率限制用）。

### 從舊版升級

- `API_SECRET_KEY` 如果還是 `changeme`，先換掉再啟動，否則 backend 起不來。
- backend 啟動時會自動更新資料庫 schema：`users.id` 從 Telegram 的數字 ID 改成
  `平台:ID`（既有資料會轉成 `telegram:<原本的 ID>`），不需要手動處理。**升級前建議先備份資料庫。**
- 後台已存的 LLM API Key 會在啟動時自動加密，不用重新輸入。
- 所有管理員需要重新登入一次（session token 改成雜湊後才存進資料庫）。
- `request_logs` 預設只保留 30 天，升級後第一次啟動就會清掉更舊的紀錄；
  想保留請先設定 `LOG_RETENTION_DAYS=0`。

---

## 環境變數

| 變數 | 必填 | 說明 |
|------|------|------|
| `POSTGRES_USER` | ✓ | 資料庫帳號 |
| `POSTGRES_PASSWORD` | ✓ | 資料庫密碼 |
| `POSTGRES_DB` | ✓ | 資料庫名稱 |
| `API_SECRET_KEY` | ✓ | bot 呼叫 backend 內部端點的共享密鑰，同時是 LLM API Key 的加密金鑰來源。至少 16 個字元，不可用 `changeme`。換掉之後要到後台重新輸入 LLM API Key |
| `TELEGRAM_BOT_TOKEN` | 使用 Telegram 時必填 | 從 @BotFather 取得 |
| `LINE_CHANNEL_SECRET` | 使用 LINE 時必填 | LINE Developers Console |
| `LINE_CHANNEL_ACCESS_TOKEN` | 使用 LINE 時必填 | LINE Developers Console |
| `DISCORD_BOT_TOKEN` | 使用 Discord 時必填 | Discord Developer Portal |

選填（括號內是預設值）：

| 變數 | 說明 |
|------|------|
| `RATE_LIMIT_PER_MINUTE`（10） | 每位用戶每分鐘最多幾次請求，0 = 不限制 |
| `RATE_LIMIT_PER_DAY`（200） | 每位用戶每天最多幾次請求，0 = 不限制 |
| `LLM_TIMEOUT_SECONDS`（55） | 單次 LLM 呼叫最多等幾秒，本機 Ollama 跑得慢可以調高 |
| `LOG_RETENTION_DAYS`（30） | `request_logs` 保留天數，0 = 永久保留 |
| `MESSAGE_RETENTION_DAYS`（0） | 對話內容保留天數，0 = 永久保留 |
| `CORS_ORIGINS`（`http://localhost:5173`） | 允許跨來源呼叫後台 API 的來源，逗號分隔，只有本機 `npm run dev` 會用到 |

> LLM provider、model、API key 透過管理後台設定，不需要寫在 `.env`。API key 會加密後才存進資料庫。

### 使用限制

- 單次輸入最多 1000 字，回覆最多 1500 字。
- 每位用戶有頻率上限（見上表），超過會請對方等一下。計數存在 backend 記憶體裡，重啟後歸零。
- 只有開啟那場對話的人可以按「再毒一點 / 再誇一點」，群組裡其他人按了不算。
- 後台登入：同一個來源 IP 對同一個帳號連續失敗 5 次會被擋 15 分鐘。

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
- Quick Reply 按鈕「再毒一點 / 再誇一點」繼續升級，「換個目標 / 換個情況」顯示使用說明

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
users         — 用戶基本資料（id 格式為「平台:平台上的用戶 ID」，例如 telegram:123456、line:Uabc…、discord:987654）
sessions      — 每次對話的 session（mode: roast | excuse）
messages      — 每條訊息記錄
app_settings  — 後台設定（provider、model、api key 等，api key 為加密儲存）
admin_users   — 後台管理員帳號（密碼為 bcrypt 雜湊）
admin_sessions — 後台登入 session（只存 token 的 SHA-256）
request_logs  — API 請求紀錄

Schema 定義在 backend/db/init.sql，backend 每次啟動都會重放一次（全部語句都可重複執行），
所以改 schema 時直接在那份檔案裡加可重複執行的語句即可。
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
