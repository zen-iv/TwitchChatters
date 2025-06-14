import aiohttp
import re
import random

class AIClient:
    def __init__(self, ai_config, personality):
        self.api_url = ai_config['api_url']
        self.params = personality.response_params
        self.system_prompt = personality.system_prompt
        self.background = personality.background
        self.examples = personality.examples

    async def generate_response(self, text):
        messages = [
            {"role": "system", "content": f"{self.system_prompt}\nКонтекст: {self.background}\nПримеры:\n{self.examples}\n\nОтвечай коротко и уместно, используя смайлы."},
            {"role": "user", "content": text}
        ]

        async with aiohttp.ClientSession() as session:
            payload = {
                "messages": messages,
                "temperature": self.params.get("temperature", 1.0),
                "max_tokens": self.params.get("max_tokens", 512),
                "top_p": self.params.get("top_p", 0.95),
                "frequency_penalty": self.params.get("frequency_penalty", 0.2),
                "presence_penalty": self.params.get("presence_penalty", 0.4),
                "stop": ["\n", "</s>"]
            }
            async with session.post(self.api_url, json=payload, timeout=20) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return self.postprocess(data["choices"][0]["message"]["content"].strip())
                else:
                    print(f"Ошибка LM Studio API: {resp.status}, {await resp.text()}")
                    return None

    def postprocess(self, text):
        text = re.sub(r"(персонаж|бот|ответ|Question|Answer|:)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"[\[\]{}()#]", "", text)
        if random.random() < 0.15:
            text = self.add_typos(text)
        return text[:100].strip()

    def add_typos(self, text):
        return ''.join([c*2 if random.random() < 0.1 else c for c in text])
