from utils.log import init_logger

LOG = init_logger('uart', 'warn')
LOG_SEND = init_logger('send', 'debug')
LOG_RECEIVE = init_logger('receive', 'debug')

PATH_DEVICES = '/sys/bus/usb/devices/*-'
PATH_USB_TTY = ':*/'
