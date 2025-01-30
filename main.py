import asyncio
import aiohttp
import random
import time
import yaml
import re
import os
from dataclasses import dataclass
from typing import Dict, Optional
from twitchio.ext import commands
from multiprocessing import Process, Queue, Manager
from dotenv import load_dotenv
from stt import audio_capture_process
from gui import BotGUI  # Теперь безопасный импорт
from shared import BROADCAST_COMMAND  # Импорт из shared.py


# Конфигурация
MESSAGE_COOLDOWN = (30, 60)
MAX_LISTEN_TIME = 60
RANDOM_SEND_DELAY = (15, 30)
LAUGHTER_EMOTES = ["Kappa", "Jebaited", "KomodoHype", "LUL", "OhMyDog", "CoolStoryBob"]
LAUGHTER_TEXT_PATTERNS = [
    r"\bха+\b", r"\bха{2,}\b", r"\bхихи\b", r"\b(ха\s?){2,}\b"
]

# Классы данных
@dataclass
class Personality:
    name: str
    system_prompt: str
    response_params: dict

@dataclass
class AccountConfig:
    username: str
    oauth: str
    channel: str
    personality: str

# Основная логика бота
class Bot(commands.Bot):
    def __init__(self, account: AccountConfig, personalities: Dict[str, Personality], 
                 ai_config: dict, queue: Queue, total_bots: int):
        super().__init__(
            token=account.oauth,
            prefix="!",
            initial_channels=[account.channel]
        )
        self.account = account
        self.personality = personalities.get(account.personality)
        self.ai_config = ai_config
        self.queue = queue
        self.total_bots = total_bots
        self.channel = None
        self.buffer = []
        self.last_processed = 0
        self.processing_task = None
        self.buffer_start_time = 0
        self.send_lock = asyncio.Lock()

    async def send_emote(self, emote: str):
        async with self.send_lock:
            if self.channel:
                try:
                    await self.channel.send(emote)
                    print(f"[{self.account.username}] Смех! Отправлено: {emote}")
                except Exception as e:
                    print(f"[{self.account.username}] Ошибка отправки эмодзи: {str(e)}")

    async def _process_buffer(self):
        if self.processing_task and not self.processing_task.done():
            return

        async def process():
            try:
                current_cooldown = random.randint(*MESSAGE_COOLDOWN)
                elapsed_time = time.time() - self.buffer_start_time

                wait_time = max(0, min(current_cooldown - elapsed_time, MAX_LISTEN_TIME - elapsed_time))
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

                full_text = " ".join(self.buffer)
                self.buffer.clear()
                self.last_processed = time.time()

                response = await self._generate_response(full_text)
                if response:
                    async with self.send_lock:
                        if self.channel:
                            await asyncio.sleep(random.uniform(*RANDOM_SEND_DELAY))
                            await self.channel.send(response)
                            print(f"[{self.account.username}] Отправлено: {response}")
            except Exception as e:
                print(f"[{self.account.username}] Ошибка обработки буфера: {e}")

        self.processing_task = asyncio.create_task(process())

    async def queue_listener(self):
        while True:
            try:
                data = await asyncio.to_thread(self.queue.get)
                if isinstance(data, tuple) and data[0] == 'laughter':
                    await self.send_emote(random.choice(LAUGHTER_EMOTES))
                elif isinstance(data, str):
                    text = data
                    if any(re.search(pattern, text, re.IGNORECASE) for pattern in LAUGHTER_TEXT_PATTERNS):
                        await self.send_emote(random.choice(LAUGHTER_EMOTES))
                    elif "боты плюс" in text.lower():
                        for _ in range(self.total_bots):
                            self.queue.put(BROADCAST_COMMAND)
                    elif BROADCAST_COMMAND in text:
                        await self._send_plus()
                    else:
                        now = time.time()
                        if now - self.last_processed < MESSAGE_COOLDOWN[0]:
                            self.buffer.append(text)
                            asyncio.create_task(self._process_buffer())
                        else:
                            self.buffer = [text]
                            self.buffer_start_time = now
                            asyncio.create_task(self._process_buffer())
            except Exception as e:
                print(f"[{self.account.username}] Ошибка в слушателе очереди: {e}")

    async def _send_plus(self):
        try:
            async with self.send_lock:
                if self.channel:
                    await self.channel.send("+")
                    print(f"[{self.account.username}] Отправлено: +")
        except Exception as e:
            print(f"[{self.account.username}] Ошибка отправки '+': {str(e)}")

    async def _generate_response(self, text: str) -> Optional[str]:
        try:
            print(f"[{self.account.username}] Генерация ответа для: {text}")
            async with aiohttp.ClientSession() as session:
                payload = {
                    "messages": [
                        {"role": "system", "content": self.personality.system_prompt},
                        {"role": "user", "content": text}
                    ],
                    "temperature": self.personality.response_params.get("temperature", 0.7),
                    "max_tokens": 400,
                    "top_p": 0.9,
                    "frequency_penalty": 0.5,
                    "presence_penalty": 0.3,
                    "stop": ["\n", "###", "</s>"]
                }
                async with session.post(
                    self.ai_config['api_url'],
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        print(f"[{self.account.username}] API ошибка {response.status}: {error}")
                        return None

                    data = await response.json()
                    response_text = data["choices"][0]["message"]["content"].strip()
                    print(f"[{self.account.username}] Сгенерирован ответ: {response_text}")
                    return response_text
        except Exception as e:
            print(f"[{self.account.username}] Ошибка генерации: {e}")
            return None

    async def event_ready(self):
        print(f"[{self.account.username}] Успешный запуск!")
        self.channel = self.get_channel(self.account.channel.lstrip('#'))
        if self.channel:
            print(f"[{self.account.username}] Подключен к каналу: {self.channel.name}")
            asyncio.create_task(self.queue_listener())

# Функция для замены переменных в YAML
def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # Рекурсивно заменяем ${...} на значения из окружения
    def replace_env_vars(data):
        if isinstance(data, dict):
            return {k: replace_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [replace_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            var_name = data[2:-1]
            return os.getenv(var_name)
        return data
    
    return replace_env_vars(config)

# Функция-обертка для запуска бота
def bot_runner(account_dict: dict, personality_dict: dict, ai_config: dict, queue: Queue, total_bots: int):
    account = AccountConfig(**account_dict)
    personality = Personality(**personality_dict)
    
    bot = Bot(
        account=account,
        personalities={personality.name: personality},
        ai_config=ai_config,
        queue=queue,
        total_bots=total_bots
    )
    bot.run()

if __name__ == "__main__":
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    load_dotenv()
    config = load_config()
    print(config["accounts"][0]["oauth"])
    
    manager = Manager()
    config['queue'] = manager.Queue()
    
    audio_proc = Process(target=audio_capture_process, args=(config['queue'], config['stt']))
    audio_proc.start()
    
    gui = BotGUI(config, audio_proc, config['queue'])
    gui.mainloop()