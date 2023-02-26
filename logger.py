from os import getcwd
from loguru import logger


logger.add(
    sink=getcwd() + '/logs/logfile.log',
    format="{time:DD.MM.YYYY at HH:mm:ss} {level} {function} {message}",
    level="INFO",
    rotation="128 MB"
)
