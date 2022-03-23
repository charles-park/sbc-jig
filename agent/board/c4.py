from gpio import GPIO

'''
+-----+-----+-----+
|     | 1.4 | 1.2 |
| ETH +-----+-----+
|     | 1.1 | 1.3 |
+-----+-----+-----+
'''
class C4():
    model = 'C4'
    uart = '/dev/ttyS0'
    usb_node = [{'node': '1.4', 'speed': None}, {'node': '1.1', 'speed': None},
            {'node': '1.2', 'speed': None}, {'node': '1.3', 'speed': None}]
    pins = GPIO(model)
