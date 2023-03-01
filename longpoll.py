from vk_api.bot_longpoll import VkBotLongPoll
from logger import logger


class MyVkBotLongPoll(VkBotLongPoll):
    def listen(self):
        while True:
            try:
                for event in self.check():
                    yield event
            except Exception as e:
                logger.exception(e)
