from utils.log import init_logger

LOG = init_logger('iperf', 'debug')

_PARALLEL = 1

SET_TIME = 10
ERROR = 'error'
DONE = 'done'

MSG_IPERF_START = 'request,iperf,start'
MSG_IPERF_STOP = 'request,iperf,stop'
