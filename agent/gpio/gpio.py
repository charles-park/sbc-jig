from gpio.pin import *

gpa0_2 = Pin(0x9, 0x8, 'GPA0_2')
gpa0_3 = Pin(0x9, 0xc, 'GPA0_3')
gpa0_0 = Pin(0x9, 0x9, 'GPA0_0')
gpa2_7 = Pin(0x9, 0xd, 'GPA2_7')
gpa0_1 = Pin(0x9, 0xa, 'GPA0_1')
gpa2_6 = Pin(0x9, 0xe, 'GPA2_6')
gpa2_4 = Pin(0x9, 0xb, 'GPA2_4')
gpa2_5 = Pin(0x9, 0xf, 'GPA2_5')

gpx1_5 = Pin(0xa, 0x8, 'GPX1_5')
gpb3_3 = Pin(0xa, 0xc, 'GPB3_3')
gpx1_2 = Pin(0xa, 0x9, 'GPX1_2')
gpb3_2 = Pin(0xa, 0xd, 'GPB3_2')
gpx1_6 = Pin(0xa, 0xa, 'GPX1_6')
gpx1_3 = Pin(0xa, 0xe, 'GPX1_3')
gpx2_6 = Pin(0xa, 0xb, 'GPX2_6')
gpx2_4 = Pin(0xa, 0xf, 'GPX2_4')

gpx2_5 = Pin(0xb, 0x8, 'GPX2_5')
gpx2_7 = Pin(0xb, 0xc, 'GPX2_7')
gpx2_1 = Pin(0xb, 0x9, 'GPX2_1')
gpx1_7 = Pin(0xb, 0xd, 'GPX1_7')
gpx2_0 = Pin(0xb, 0xa, 'GPX2_0')
gpx3_1 = Pin(0xb, 0xe, 'GPX3_1')
gpa2_2 = Pin(0xb, 0xb, 'GPA2_2')
gpx3_2 = Pin(0xb, 0xf, 'GPX3_2')

gpa2_3 = Pin(0x18, 0x8, 'GPA2_3')
gpz_0 = Pin(0x18, 0xc, 'GPZ_0')
gpz_1 = Pin(0x18, 0x9, 'GPZ_1')
gpz_4 = Pin(0x18, 0xd, 'GPZ_4')
gpz_2 = Pin(0x18, 0xa, 'GPZ_2')
gpz_3 = Pin(0x18, 0xe, 'GPZ_3')

GPIOS_XU4 = [gpa0_2, gpa0_3, gpa0_0, gpa2_7, gpa0_1, gpa2_6, gpa2_4, gpa2_5,
        gpx1_5, gpb3_3, gpx1_2, gpb3_2, gpx1_6, gpx1_3, gpx2_6, gpx2_4, gpx2_5,
        gpx2_7, gpx2_1, gpx1_7, gpx2_0, gpx3_1, gpa2_2, gpx3_2, gpa2_3, gpz_0,
        gpz_1, gpz_4, gpz_2, gpz_3]

V5_0 = Pin(0x8, 0x8, 'V5_0')
V5_1 = Pin(0x8, 0x9, 'V5_1')
V18_0 = Pin(0x8, 0xa, 'V18_0')
V18_1 = Pin(0x8, 0xe, 'V18_1')

PWRS_XU4 = [V18_0, V18_1]

led_sys = Pin(0x19, 0x8, "SYS", high=0.6, low=0.1)
led_pwr = Pin(0x19, 0xc, "PWR", high=0.6, low=0.1)

led_eth_y = Pin(0x19, 0x9, "ETH_Y", high=0.6, low=0.1)
led_eth_g = Pin(0x19, 0xd, "ETH_G", high=0.6, low=0.1)

FAN_SYS = Pin(0x18, 0xb, 'PIN1')
FAN_PWM = Pin(0x18, 0xf, 'PIN2')
FAN_XU4 = [FAN_SYS, FAN_PWM]

CEC = Pin(0x8, 0xf, "CEC", high=2.5, low=0.3)
SCL = Pin(0x19, 0xf, "SCL", high=3.5, low=0.3)
SDA = Pin(0x19, 0xb, "SDA", high=3.5, low=0.3)

HDMI_XU4 = [CEC, SCL, SDA]
LED_ETH_XU4 = [led_eth_y, led_eth_g]
LED_SYS_XU4 = [led_sys, led_pwr]

class GPIO():
    def __init__(self, model):
        if model == 'XU4':
            self.gpios = GPIOS_XU4
            self.pwrs = PWRS_XU4
            self.led_sys = led_sys
            self.led_pwr = led_pwr
            self.led_eth = LED_ETH_XU4
            self.fan = FAN_XU4
            self.hdmi = [CEC, SCL, SDA]
