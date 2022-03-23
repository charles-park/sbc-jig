import logging
import colorlog
from colorlog import ColoredFormatter

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

formatter_uart = ColoredFormatter(
    "%(log_color)s[%(asctime)s] %(name)s --- %(message)s ---",
    datefmt='%M:%S',
    reset=True,
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'white,bold',
        'INFOV':    'cyan,bold',
        'WARNING':  'yellow',
        'ERROR':    'red,bold',
        'CRITICAL': 'red,bg_white',
    },
    secondary_log_colors={},
    style='%'
)

formatter = ColoredFormatter(
    "%(log_color)s[%(asctime)s] %(name)s.%(funcName)s --- %(message)s ---",
    datefmt='%M:%S',
    reset=True,
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'white,bold',
        'INFOV':    'cyan,bold',
        'WARNING':  'yellow',
        'ERROR':    'red,bold',
        'CRITICAL': 'red,bg_white',
    },
    secondary_log_colors={},
    style='%'
)

def init_logger(dunder_name, testing_mode='info') -> logging.Logger:
    handler = logging.StreamHandler()
    if dunder_name == 'send' or dunder_name == 'receive':
        handler.setFormatter(formatter_uart)
    else:
        handler.setFormatter(formatter)
    logger = logging.getLogger(dunder_name)
    logger.handlers = []
    logger.propagate = False
    logger.addHandler(handler)

    if testing_mode == 'debug':
        logger.setLevel(logging.DEBUG)
    elif testing_mode == 'warn':
        logger.setLevel(logging.WARN)
    else:
        logger.setLevel(logging.INFO)

    return logger
