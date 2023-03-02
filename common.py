import os
from vk_api.exceptions import Captcha


def auth_handler():
    code = input('Authentication code: ')
    return code, False


def captcha_handler(captcha: Captcha):
    print('Captcha handler:', captcha)
    code = input("Enter captcha code {0}: ".format(captcha.get_url())).strip()
    return captcha.try_again(code)


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
