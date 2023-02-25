import os
import vk_api
import youtube_dl
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from dotenv import load_dotenv
from telebot import TeleBot, types, formatting


def auth_handler():
    key = input('Authentication code: ')
    return key, False


def captcha_handler(captcha):
    print('Captcha handler:', captcha)
    key = input("Enter captcha code {0}: ".format(captcha.get_url())).strip()
    return captcha.try_again(key)


def get_largest_image_url_v2(sizes: list) -> str:
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
        print('Vk auth ERROR:', e, sep='\n')
        return

    vk_longpoll = VkBotLongPoll(
        vk_api.VkApi(token=os.getenv('VK_GROUP_TOKEN')),
        os.getenv('VK_GROUP_ID')
    )

    tg_bot = TeleBot(os.getenv('TG_TOKEN'))
    tg_chat_id = os.getenv('TG_CHAT_ID')

    for event in vk_longpoll.listen():
        if event.type == VkBotEventType.WALL_POST_NEW and event.obj.post_type == 'post':

            media_group = []
            video_urls = []
            opened_files = []

            for attachment in event.obj.attachments:
                if attachment['type'] == 'photo':
                    photo_url = get_largest_image_url(attachment['photo']['sizes'])
                    media_group.append(types.InputMediaPhoto(photo_url))

                if attachment['type'] == 'video':
                    owner_id = str(attachment['video']['owner_id']).replace('-', '')
                    video_id = str(attachment['video']['id'])

                    videos = vk_session.method('video.get', {
                        'owner_id': owner_id,
                        'videos': f"{str(attachment['video']['owner_id'])}_{video_id}"
                    })

                    video_urls.append(videos['items'][0]['player'])

            try:
                ydl_opts = {
                    'outtmpl': f'videos/%(title)s-%(id)s.%(ext)s'
                }
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download(video_urls)
            except Exception as e:
                print('Download VIDEOS error:', e, sep='\n')

            for adrs, _, files in os.walk('videos'):
                for file in files:
                    tmp = open(os.path.join(adrs, file), 'rb')
                    opened_files.append(tmp)
                    media_group.append(types.InputMediaVideo(tmp))

            if len(media_group) == 0:
                continue

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

            media_group[0].parse_mode = 'HTML'
            media_group[0].caption = caption

            try:
                tg_bot.send_media_group(
                    chat_id=tg_chat_id,
                    media=media_group
                )
            except Exception as e:
                print('Send MEDIA exception:', e, sep='\n')

            for o_file in opened_files:
                o_file.close()

            for adrs, _, files in os.walk('videos'):
                for file in files:
                    os.remove(os.path.join(adrs, file))


if __name__ == '__main__':
    try:
        os.mkdir('videos')
    except FileExistsError:
        pass

    load_dotenv()
    main()
