from twitchio.ext import commands
from modules.ai_client import AIClient
from modules.utils import AccountConfig, Personality
import asyncio
import random
import re

class TwitchBot(commands.Bot):
    def __init__(self, account: AccountConfig, personality: Personality, ai_config, queue):
        super().__init__(token=account.oauth, prefix="!", initial_channels=[account.channel])
        self.account = account
        self.personality = personality
        self.ai_client = AIClient(ai_config, personality)
        self.queue = queue
        self.channel = None

    async def event_ready(self):
        print(f"{self.account.username} запущен.")
        self.channel = self.get_channel(self.account.channel.lstrip('#'))
        asyncio.create_task(self.message_loop())

    async def message_loop(self):
        while True:
            text = await asyncio.to_thread(self.queue.get)
            if text and self.validate_message(text):
                response = await self.ai_client.generate_response(text)
                if response:
                    delay = random.uniform(1.0, 2.5)
                    await asyncio.sleep(delay)
                    print(f"[{self.account.username}] Отправлено: {response}")  # <-- вывод в консоль
                    await self.channel.send(response)

    def validate_message(self, text):
        return len(text) > 3 and not re.search(r"http|@|[\U0001F600-\U0001F64F]", text)

def bot_runner(account_dict, personality_obj, ai_config, queue):
    account = AccountConfig(**account_dict)
    bot = TwitchBot(account, personality_obj, ai_config, queue)
    bot.run()
