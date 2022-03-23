
class Pin:
    def __init__(self, addr, channel, label, high=1, low=0):
        self.addr = addr
        self.channel = channel
        self.label = label
        self.high = high
        self.low = low
