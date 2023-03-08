import os
import vk_api
from typing import Union
from common import auth_handler, captcha_handler
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


def get_vk_session() -> Union[vk_api.VkApi, None]:
    vk_session = vk_api.VkApi(
        login=os.getenv('VK_LOGIN'),
        password=os.getenv('VK_PASSWORD'),
        auth_handler=auth_handler,
        captcha_handler=captcha_handler
    )

    try:
        vk_session.auth(token_only=True)
    except Exception as e:
        logger.error(f"Vk auth error:\n{e}")
        return None

    return vk_session


def get_vk_longpoll() -> Union[MyVkBotLongPoll, None]:
    vk_longpoll = None
    try:
        vk_longpoll = MyVkBotLongPoll(
            vk_api.VkApi(token=os.getenv('VK_GROUP_TOKEN')),
            os.getenv('VK_GROUP_ID')
        )
    except Exception as e:
        logger.exception(f"Create Vk lonpoll:\n{e}")

    return vk_longpoll
