import httpx
from app.config import settings

REFLECT_SUFFIX = (
    "\n\n先在腦中想兩到三個不同方向的版本，選最到位的那個輸出。"
    "只輸出最終版本，不要顯示思考過程或任何前言。"
)

VENOM_PROMPTS = {
    1: (
        "用損友的口氣評論下面這句話，像在跟認識很久的朋友說話，"
        "輕鬆嘲諷但不傷感情，口語化、不要文謅謅，50字以內。"
    ),
    2: (
        "用刻薄但說得有點道理的方式評論下面這句話，嘴壞但不是無腦亂罵，"
        "像那種讓人反駁不了的損，60字以內。"
    ),
    3: (
        "精準找到下面這句話最脆弱的點，字字帶刺，直接戳下去，"
        "不留情面，語氣像老司機嗆新手，70字以內。"
    ),
    4: (
        "全力開炮評論下面這句話，語氣強烈到讓人啞口無言，"
        "像吵架要贏的那種說法，80字以內。"
    ),
    5: (
        "這是你最巔峰的評論，針對下面這句話，每個字都有重量，"
        "讓人又笑又想翻白眼，100字以內。"
    ),
}

NUCLEAR_PROMPT = (
    "這是你的終極一擊，把所有的毒都集中起來，"
    "針對這句話來一個讓人永生難忘、啞口無言但又忍不住大笑的評論，"
    "150字以內，句句都是精華。"
)

EXCUSE_PROMPTS = {
    1: (
        "幫下面這個情況想一個借口，聽起來要合理可信，像真人在解釋，"
        "口語化、自然，不要太正式，60字以內。"
    ),
    2: (
        "幫下面這個情況想一個誇張版借口，要有點戲劇性，像在博同情那種，"
        "聽起來很可憐但又不完全不合理，80字以內。"
    ),
    3: (
        "幫下面這個情況想一個離譜的借口，越荒唐越好，"
        "但語氣要非常認真、超有自信，像真的在解釋一件嚴肅的事，100字以內。"
    ),
    4: (
        "幫下面這個情況想一個超展開的借口，要牽扯到完全不相關的第三者或意外事件，"
        "情節越曲折越好，但說得一臉無辜，120字以內。"
    ),
    5: (
        "幫下面這個情況想一個宇宙級的借口，可以扯到天災、量子力學、祖先、命運、"
        "或任何荒謬的宏觀原因，語氣要像在做學術報告，140字以內。"
    ),
    6: (
        "這是終極借口，幫下面這個情況想一個讓人聽完當場無法反駁、"
        "邏輯自洽但離現實十萬八千里的傳說級借口，語氣超級認真，"
        "像在讀遺囑，160字以內。"
    ),
}

ESCALATE_ROAST_SUFFIX = "上一個版本太溫柔了，這次要比剛才更毒、更精準、更讓人無言。重新生成。"
ESCALATE_EXCUSE_SUFFIX = "上一個版本不夠看，這次要比剛才更誇張、更荒唐、更讓人傻眼。重新生成。"


async def _call_ollama(
    system_prompt: str,
    user_input: str,
    previous_output: str | None = None,
    input_label: str = "情況",
) -> str:
    messages = [
        {"role": "system", "content": system_prompt + REFLECT_SUFFIX},
        {"role": "user", "content": f"{input_label}：「{user_input}」"},
    ]

    if previous_output:
        messages.append({"role": "assistant", "content": previous_output})
        messages.append({"role": "user", "content": ESCALATE_ROAST_SUFFIX if input_label == "用戶說" else ESCALATE_EXCUSE_SUFFIX})

    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()


async def generate_roast(
    content: str,
    venom_level: int,
    is_nuclear: bool = False,
    previous_output: str | None = None,
) -> str:
    prompt = NUCLEAR_PROMPT if is_nuclear else VENOM_PROMPTS.get(venom_level, VENOM_PROMPTS[1])
    return await _call_ollama(prompt, content, previous_output=previous_output, input_label="用戶說")


async def generate_excuse(
    situation: str,
    excuse_level: int,
    previous_output: str | None = None,
) -> str:
    prompt = EXCUSE_PROMPTS.get(excuse_level, EXCUSE_PROMPTS[1])
    return await _call_ollama(prompt, situation, previous_output=previous_output, input_label="情況")
