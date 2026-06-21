from __future__ import annotations
from app.services import app_settings as cfg

REFLECT_SUFFIX = (
    "\n\n選最犀利、最到位的方式回應，直接輸出結果，不要有任何前言、解釋或思考過程。"
    "嚴格遵守字數限制。"
    "一律用繁體中文回覆，除非是特定專有名詞、英文梗或網路用語才可以保留原文。"
)

VENOM_PROMPTS = {
    1: (
        "你是個損友，對方剛說了一句話。"
        "先搞清楚他在說什麼、想表達什麼，然後用輕鬆嘲諷的口氣回他一句，"
        "針對他說的內容，像真的在回應朋友，口語化不文謅謅，50字以內。"
    ),
    2: (
        "你是個嗆辣高手，對方剛說了一句話。"
        "讀懂他話裡的意思，找出最值得嘲諷的點，"
        "用刻薄但說得有道理的方式回他，讓他反駁不了，60字以內。"
    ),
    3: (
        "你是嗆辣老手，對方剛說了一句話。"
        "完全理解他在說什麼，精準找到那句話裡最脆弱的點，"
        "字字帶刺直接戳下去，不留情面，語氣犀利不客氣，70字以內。"
    ),
    4: (
        "你是辯論賽冠軍，對方剛說了一句話。"
        "讀透他每個字的意思，找出最致命的切入點，"
        "全力開炮回他，說到他啞口無言，語氣強烈，80字以內。"
    ),
    5: (
        "你是嗆辣界封神的存在，對方剛說了一句話。"
        "讀透他話裡每個字背後的意思，挑最要命的那個點，"
        "用最犀利的方式精準回擊，讓人又笑又想翻白眼，每個字都有重量，100字以內。"
    ),
}

NUCLEAR_PROMPT = (
    "這是你的終極一擊。對方剛說了一句話，先完全讀懂他的意思，"
    "然後把所有的毒都集中起來，針對他說的這件事，"
    "給一個讓人永生難忘、啞口無言但又忍不住大笑的回擊，150字以內，句句都是精華。"
)

EXCUSE_PROMPTS = {
    1: (
        "仔細讀懂下面的情況是什麼、對方需要解釋什麼，"
        "然後針對這個具體情況想一個借口，聽起來要合理可信，像真人在解釋，口語化、自然，不要太正式，60字以內。"
    ),
    2: (
        "仔細讀懂下面的情況是什麼、對方需要解釋什麼，"
        "針對這個具體情況想一個誇張版借口，要有點戲劇性，像在博同情那種，聽起來很可憐但又不完全不合理，80字以內。"
    ),
    3: (
        "仔細讀懂下面的情況是什麼、對方需要解釋什麼，"
        "針對這個具體情況想一個離譜的借口，越荒唐越好，但語氣要非常認真、超有自信，像真的在解釋一件嚴肅的事，100字以內。"
    ),
    4: (
        "仔細讀懂下面的情況是什麼、對方需要解釋什麼，"
        "針對這個具體情況想一個超展開的借口，要牽扯到完全不相關的第三者或意外事件，情節越曲折越好，但說得一臉無辜，120字以內。"
    ),
    5: (
        "仔細讀懂下面的情況是什麼、對方需要解釋什麼，"
        "針對這個具體情況想一個宇宙級的借口，可以扯到天災、量子力學、祖先、命運，語氣要像在做學術報告，140字以內。"
    ),
    6: (
        "仔細讀懂下面的情況是什麼、對方需要解釋什麼，"
        "針對這個具體情況給出終極借口：讓人聽完當場無法反駁、邏輯自洽但離現實十萬八千里的傳說級借口，語氣超級認真，像在讀遺囑，160字以內。"
    ),
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
            "上一個版本太溫柔了，這次要比剛才更狠、更精準，找更致命的點下手，重新生成。"
            if is_roast else
            "上一個版本太保守了，這次要更誇張：扯更多不相關的事、語氣更嚴肅認真、情節更曲折離奇，重新生成。"
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
    messages = _build_messages(prompt, content, "對方說", previous_output, is_roast=True)
    return await _call(messages)


async def generate_excuse(
    situation: str,
    excuse_level: int,
    previous_output: str | None = None,
) -> str:
    prompt = EXCUSE_PROMPTS.get(excuse_level, EXCUSE_PROMPTS[1])
    messages = _build_messages(prompt, situation, "情況", previous_output, is_roast=False)
    return await _call(messages)
