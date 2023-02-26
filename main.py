import os
import time
import vk_api
import youtube_dl
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from dotenv import load_dotenv
from telebot import TeleBot, types, formatting
from logger import logger


def auth_handler():
    key = input('Authentication code: ')
    return key, False


def captcha_handler(captcha):
    print('Captcha handler:', captcha)
    key = input("Enter captcha code {0}: ".format(captcha.get_url())).strip()
    return captcha.try_again(key)


def get_largest_image_url(sizes: list) -> str:
    urls = {size['type']: index for index, size in enumerate(sizes)}
    if 'w' in urls:
        return sizes[urls['w']]['url']
    elif 'z' in urls:
        return sizes[urls['z']]['url']
    elif 'y' in urls:
        return sizes[urls['y']]['url']
    elif 'x' in urls:
        return sizes[urls['x']]['url']
    elif 'r' in urls:
        return sizes[urls['r']]['url']
    else:
        return sizes[0]['url']


def clear_videos_dir() -> None:
    for adrs, _, files in os.walk('videos'):
        for file in files:
            os.remove(os.path.join(adrs, file))


def main():
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
        return

    vk_longpoll = VkBotLongPoll(
        vk_api.VkApi(token=os.getenv('VK_GROUP_TOKEN')),
        os.getenv('VK_GROUP_ID')
    )

    tg_bot = TeleBot(os.getenv('TG_TOKEN'))
    tg_chat_id = os.getenv('TG_CHAT_ID')

    for event in vk_longpoll.listen():
        if event.type == VkBotEventType.WALL_POST_NEW and event.obj.post_type == 'post':

            photo_urls = []
            video_urls = []
            opened_videos = []

            for attachment in event.obj.attachments:
                if attachment['type'] == 'photo':
                    photo_urls.append(get_largest_image_url(attachment['photo']['sizes']))

                if attachment['type'] == 'video':
                    owner_id = str(attachment['video']['owner_id']).replace('-', '')
                    video_id = str(attachment['video']['id'])

                    try:
                        videos = vk_session.method('video.get', {
                            'owner_id': owner_id,
                            'videos': f"{str(attachment['video']['owner_id'])}_{video_id}"
                        })
                        video_urls.append(videos['items'][0]['player'])
                    except Exception as e:
                        logger.error(f"Vk video.get error:\n{e}")

            try:
                ydl_opts = {
                    'outtmpl': f'videos/%(title)s-%(id)s.%(ext)s'
                }
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download(video_urls)
            except Exception as e:
                logger.error(f"Download videos error:\n{e}")

            for adrs, _, files in os.walk('videos'):
                for file in files:
                    opened_videos.append(open(os.path.join(adrs, file), 'rb'))

            caption = f'{event.obj.text}'
            if event.obj.signer_id is not None:
                from_user = vk_session.method('users.get', {
                    'user_ids': event.obj.signer_id
                })

                if len(from_user) > 0:
                    vk_user_link = formatting.hlink(
                        from_user[0]['last_name'] + ' ' + from_user[0]['first_name'],
                        f'https://vk.com/id{event.obj.signer_id}')
                    caption += f"\n\nАвтор - {vk_user_link}"
                else:
                    caption += f"\n\nАвтор - https://vk.com/id{event.obj.signer_id}"

            if not photo_urls and not opened_videos:
                try:
                    tg_bot.send_message(
                        chat_id=tg_chat_id,
                        text=caption,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Send text only error:\n{e}")
                continue

            if len(photo_urls) == 1 and not opened_videos:
                try:
                    tg_bot.send_photo(
                        chat_id=tg_chat_id,
                        photo=photo_urls[0],
                        caption=caption
                    )
                except Exception as e:
                    logger.error(f"Telegram sendPhoto error:\n{e}")
                continue

            if len(opened_videos) == 1 and not photo_urls:
                try:
                    tg_bot.send_video(
                        chat_id=tg_chat_id,
                        video=opened_videos[0],
                        caption=caption
                    )
                except Exception as e:
                    logger.error(f"Telegram sendVideo error:\n{e}")

                opened_videos[0].close()
                clear_videos_dir()

            media_group = []
            for photo_url in photo_urls:
                media_group.append(types.InputMediaPhoto(photo_url))
            for o_video in opened_videos:
                media_group.append(types.InputMediaVideo(o_video))

            media_group[0].parse_mode = 'HTML'
            media_group[0].caption = caption

            try:
                tg_bot.send_media_group(
                    chat_id=tg_chat_id,
                    media=media_group
                )
            except Exception as e:
                logger.error(f"Send media exception:\n{e}")

            time.sleep(2)

            for o_video in opened_videos:
                o_video.close()

            clear_videos_dir()


if __name__ == '__main__':
    try:
        os.mkdir('videos')
    except FileExistsError:
        pass

    load_dotenv()
    main()
