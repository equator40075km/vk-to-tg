import os
import youtube_dl
from common import get_largest_image_url, clear_videos_dir
from vk import get_vk_session, get_vk_longpoll
from vk_api.bot_longpoll import VkBotEventType
from dotenv import load_dotenv
from telebot import TeleBot, types, formatting
from logger import logger
from moviepy.video.io.VideoFileClip import VideoFileClip
from typing import List, IO


def main() -> None:
    vk_session = get_vk_session()
    vk_longpoll = get_vk_longpoll()
    if vk_session is None or vk_longpoll is None:
        return

    tg_bot = TeleBot(os.getenv('TG_TOKEN'))
    tg_chat_id = os.getenv('TG_CHAT_ID')

    for event in vk_longpoll.listen():
        if event.type == VkBotEventType.WALL_POST_NEW and event.obj.post_type == 'post':

            skip_post = False
            photo_urls: List[str] = []
            video_urls: List[str] = []
            video_objects = {}  # video_name -> vk video object
            opened_videos: List[IO] = []

            for attachment in event.obj.attachments:
                if attachment['type'] == 'photo':
                    photo_urls.append(get_largest_image_url(attachment['photo']['sizes']))

                elif attachment['type'] == 'video':
                    owner_id = str(attachment['video']['owner_id']).replace('-', '')
                    video_id = str(attachment['video']['id'])

                    try:
                        videos = vk_session.method('video.get', {
                            'owner_id': owner_id,
                            'videos': f"{str(attachment['video']['owner_id'])}_{video_id}"
                        })
                        video_name = f"videos/video{videos['items'][0]['owner_id']}_{videos['items'][0]['id']}"
                        video_objects[video_name] = videos['items'][0]
                        video_urls.append(videos['items'][0]['player'])
                    except Exception as e:
                        logger.error(f"Vk video.get error:\n{e}")
                        skip_post = True
                        break

                # skip post with attachment types other than [photo, video]
                else:
                    skip_post = True
                    break

            if skip_post:
                continue

            try:
                # download video
                ydl_opts = {
                    'outtmpl': f'videos/video%(id)s'
                }
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download(video_urls)
            except Exception as e:
                logger.error(f"Download videos error:\n{e}")

            # convert videos to mp4, collect opened video files for InputVideoMedia
            for adrs, _, files in os.walk('videos'):
                for file in files:
                    try:
                        v_clip = VideoFileClip(os.path.join(adrs, file))
                        v_clip.write_videofile(
                            filename=os.path.join(adrs, file) + '.mp4',
                            codec='libx264',
                            temp_audiofile=os.getcwd() + "/videos/temp_audiofile.mp4"
                        )
                        v_clip.close()
                        opened_videos.append(open(os.path.join(adrs, file) + '.mp4', 'rb'))
                    except Exception as e:
                        logger.exception(f"Convert video exception:\n{e}")
                        clear_videos_dir()

            # make caption (post text)
            caption = f'{event.obj.text}'
            if event.obj.signer_id is not None:
                from_user = {}
                try:
                    from_user = vk_session.method('users.get', {
                        'user_ids': event.obj.signer_id
                    })
                except Exception as e:
                    logger.error(f'Vk users.get error:\n{e}')

                if len(from_user) > 0:
                    vk_user_link = formatting.hlink(
                        from_user[0]['last_name'] + ' ' + from_user[0]['first_name'],
                        f'https://vk.com/id{event.obj.signer_id}')
                    caption += f"\n\n?????????? - {vk_user_link}"
                else:
                    caption += f"\n\n?????????? - https://vk.com/id{event.obj.signer_id}"

            # text only post
            if not photo_urls and not opened_videos:
                clear_videos_dir()
                continue

            # collecting media group
            media_group = []
            for photo_url in photo_urls:
                media_group.append(types.InputMediaPhoto(photo_url))
            for o_video in opened_videos:
                video_key = o_video.name.replace('.mp4', '')
                imv = types.InputMediaVideo(
                    media=o_video,
                    duration=video_objects[video_key]['duration'],
                    width=video_objects[video_key]['width'],
                    height=video_objects[video_key]['height'],
                )
                media_group.append(imv)

            # adding caption (parse_mode=HTML for link on post author)
            media_group[0].parse_mode = 'HTML'
            media_group[0].caption = caption

            try:
                tg_bot.send_media_group(
                    chat_id=tg_chat_id,
                    media=media_group
                )
            except Exception as e:
                logger.error(f"Send media exception:\n{e}")

            for o_video in opened_videos:
                o_video.close()

            clear_videos_dir()


if __name__ == '__main__':
    load_dotenv()

    try:
        os.mkdir('videos')
    except FileExistsError:
        pass

    while True:
        try:
            main()
        except Exception as e:
            logger.exception(e)
