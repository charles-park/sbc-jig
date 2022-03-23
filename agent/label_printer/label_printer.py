import sys
# needs pip install zebra
import zebra
import cups
import time


class MacPrinter(object):
    """A class to print mac address label with Zebra label printer using EPL2"""
    z = zebra.Zebra()
    label_height = (0,0)
    label_width = 0

    # epl template script
    # Q : Label height followed by gap width
    text_template = """
I8,0,001
Q76,16
q240
rN
S4
D15
ZB
JF
O
R304,8
f100
N
A16,0,0,2,1,1,N,"%s"
A16,32,0,2,1,1,N,"%s"
P1
"""

    def __init__(self, printer = "ZTC-GC420d-EPL", l_height = (80, 16), l_width = 240):
        """
        printer- name of printer queue (optional)
        l_height(label_height) - label's height and gap in dots
        l_width(label_width)
        """
        try:
            self.z.setqueue(printer)
            self.label_height = l_height
            self.label_width = l_width
            self.z.setup(
                    direct_thermal = False,
                    label_height = self.label_height,
                    label_width = self.label_width
                    )
        except:
            print('init failed')
            print('Unexcepected error: ', sys.exc_info())
            exit(-1)

    def change_printer(self, printer):
        try:
            self.z.setqueue(printer)
            self.z.setup(
                    direct_thermal = False,
                    label_height = self.label_height,
                    label_width = self.label_width
                    )
        except:
            print('Change printer failed')
            print('error: ', sys.exc_info())
            exit(-1)

    def label_print(self, channel, site, mac, err=0):
        try:
            if err == 1:
                tmp = ["", "", ""]
                idx = 0
                for i in site.split(','):
                    if len(tmp[idx] + i) > 20:
                        idx += 1
                    if idx > 2:
                        break
                    tmp[idx] += (i + ' ')
                if channel == 0:
                    side = '< '
                    self.z.output(MacPrinter.text_template_err.format(side + tmp[0], tmp[1], tmp[2]))
                    #self.z.output(MacPrinter.text_template_err.format(site, '2', '3'))
                elif channel == 1:
                    side = ' >'
                    self.z.output(MacPrinter.text_template_err.format(tmp[0] + side, tmp[1], tmp[2]))
                    #self.z.output(MacPrinter.text_template_err.format(site + side, mac, '3', '4'))
                    return

            if mac == None:
                return
            mac = mac.upper()
            if channel == 0:
                side = '< '
                self.z.output(MacPrinter.text_template % (side + site, mac))

            elif channel == 1:
                side = ' >'
                self.z.output(MacPrinter.text_template % (site + side, mac))
        except:
            print('print failed')
            print('Unexcepected error: ', sys.exc_info())
            exit(-1)


if __name__ == '__main__':
    printer_name = "ZTC-GC420d-EPL"
    print('init printer')
    printer = MacPrinter(printer = printer_name)
    print('print left')
    printer.label_print(channel=0,
            site = 'do not over',
            mac = '00:00:00:00:00:00')
    print('print right')
    printer.label_print(channel=1,
            site = '16 characters',
            mac = 'FF:FF:FF:FF:FF:FF')
