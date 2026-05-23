from __future__ import annotations
from app.services import app_settings as cfg

REFLECT_SUFFIX = (
    "\n\n先在腦中想兩到三個不同方向的版本，選最到位的那個輸出。"
    "只輸出最終版本，不要顯示思考過程或任何前言。"
)

VENOM_PROMPTS = {
    1: "用損友的口氣評論下面這句話，像在跟認識很久的朋友說話，輕鬆嘲諷但不傷感情，口語化、不要文謅謅，50字以內。",
    2: "用刻薄但說得有點道理的方式評論下面這句話，嘴壞但不是無腦亂罵，像那種讓人反駁不了的損，60字以內。",
    3: "精準找到下面這句話最脆弱的點，字字帶刺，直接戳下去，不留情面，語氣像老司機嗆新手，70字以內。",
    4: "全力開炮評論下面這句話，語氣強烈到讓人啞口無言，像吵架要贏的那種說法，80字以內。",
    5: "這是你最巔峰的評論，針對下面這句話，每個字都有重量，讓人又笑又想翻白眼，100字以內。",
}

NUCLEAR_PROMPT = (
    "這是你的終極一擊，把所有的毒都集中起來，"
    "針對這句話來一個讓人永生難忘、啞口無言但又忍不住大笑的評論，150字以內，句句都是精華。"
)

EXCUSE_PROMPTS = {
    1: "幫下面這個情況想一個借口，聽起來要合理可信，像真人在解釋，口語化、自然，不要太正式，60字以內。",
    2: "幫下面這個情況想一個誇張版借口，要有點戲劇性，像在博同情那種，聽起來很可憐但又不完全不合理，80字以內。",
    3: "幫下面這個情況想一個離譜的借口，越荒唐越好，但語氣要非常認真、超有自信，像真的在解釋一件嚴肅的事，100字以內。",
    4: "幫下面這個情況想一個超展開的借口，要牽扯到完全不相關的第三者或意外事件，情節越曲折越好，但說得一臉無辜，120字以內。",
    5: "幫下面這個情況想一個宇宙級的借口，可以扯到天災、量子力學、祖先、命運，語氣要像在做學術報告，140字以內。",
    6: "這是終極借口，讓人聽完當場無法反駁、邏輯自洽但離現實十萬八千里的傳說級借口，語氣超級認真，像在讀遺囑，160字以內。",
}


def _build_messages(
    system_prompt: str,
    user_input: str,
    input_label: str,
    previous_output: str | None,
    is_roast: bool,
) -> list[dict]:
    messages = [
        {"role": "system", "content": system_prompt + REFLECT_SUFFIX},
        {"role": "user",   "content": f"{input_label}：「{user_input}」"},
    ]
    if previous_output:
        escalate_hint = (
            "上一個版本太溫柔了，這次要比剛才更毒、更精準，重新生成。"
            if is_roast else
            "上一個版本不夠看，這次要比剛才更誇張、更荒唐，重新生成。"
        )
        messages.append({"role": "assistant", "content": previous_output})
        messages.append({"role": "user", "content": escalate_hint})
    return messages


async def _call(messages: list[dict]) -> str:
    provider = cfg.get("llm_provider")
    model    = cfg.get("llm_model")
    api_key  = cfg.get("llm_api_key")
    base_url = cfg.get("llm_base_url")

    if provider == "anthropic":
        return await _call_anthropic(messages, model, api_key)
    else:
        # openai or ollama — both use OpenAI-compatible /v1 endpoint
        effective_base = f"{base_url}/v1" if provider == "ollama" else None
        return await _call_openai_compat(messages, model, api_key, effective_base)


async def _call_openai_compat(
    messages: list[dict],
    model: str,
    api_key: str,
    base_url: str | None,
) -> str:
    from openai import AsyncOpenAI
    kwargs: dict = {"api_key": api_key or "ollama"}
    if base_url:
        kwargs["base_url"] = base_url
    client = AsyncOpenAI(**kwargs)
    resp = await client.chat.completions.create(model=model, messages=messages)
    return resp.choices[0].message.content.strip()


async def _call_anthropic(messages: list[dict], model: str, api_key: str) -> str:
    from anthropic import AsyncAnthropic
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    chat_msgs = [m for m in messages if m["role"] != "system"]
    client = AsyncAnthropic(api_key=api_key)
    resp = await client.messages.create(
        model=model,
        system=system,
        messages=chat_msgs,
        max_tokens=1024,
    )
    return resp.content[0].text.strip()


async def generate_roast(
    content: str,
    venom_level: int,
    is_nuclear: bool = False,
    previous_output: str | None = None,
) -> str:
    prompt = NUCLEAR_PROMPT if is_nuclear else VENOM_PROMPTS.get(venom_level, VENOM_PROMPTS[1])
    messages = _build_messages(prompt, content, "用戶說", previous_output, is_roast=True)
    return await _call(messages)


async def generate_excuse(
    situation: str,
    excuse_level: int,
    previous_output: str | None = None,
) -> str:
    prompt = EXCUSE_PROMPTS.get(excuse_level, EXCUSE_PROMPTS[1])
    messages = _build_messages(prompt, situation, "情況", previous_output, is_roast=False)
    return await _call(messages)
