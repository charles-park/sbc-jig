//------------------------------------------------------------------------------------------------------------
//
// ODROID-C2 GPIO/ADC/I2C/SERIAL Test Application. (Use wiringPi Library)
// Defined port number is wiringPi port number.
//
// Compile : gcc -o <create excute file name> <source file name> -lwiringPi -lwiringPiDev -lpthread
// gcc -o 40pin_test 40pin_test.c -lwiringPi -lwiringPiDev -lm -lpthread -lrt -lcrypt
// Run : sudo ./<created excute file name>
//
//------------------------------------------------------------------------------------------------------------
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <errno.h>

#include <unistd.h>
#include <string.h>
#include <time.h>
#include <sys/sysinfo.h>

#include <wiringPi.h>
#include <wiringPiI2C.h>
#include <wiringSerial.h>
#include <lcd.h>

#ifndef	TRUE
#  define	TRUE	(1==1)
#  define	FALSE	(1==2)
#endif

//------------------------------------------------------------------------------------------------------------
//
// Global handle Define
//
//------------------------------------------------------------------------------------------------------------

//------------------------------------------------------------------------------------------------------------
//
// LCD:
//
//------------------------------------------------------------------------------------------------------------
#define LCD_ROW			2	// 16 Char
#define LCD_COL			16	// 2 Line
#define LCD_BUS			4	// Interface 4 Bit mode
#define LCD_UPDATE_PERIOD	300	// 300ms

static unsigned char lcdFb[LCD_ROW][LCD_COL] = {0, };

static int lcdHandle = 0;

#define PORT_LCD_RS	7	// GPIOY.BIT3(#83)
#define PORT_LCD_E	0	// GPIOY.BIT8(#88)
#define PORT_LCD_D4	2	// GPIOX.BIT19(#116)
#define PORT_LCD_D5	3	// GPIOX.BIT18(#115)
#define PORT_LCD_D6	1	// GPIOY.BIT7(#87)
#define PORT_LCD_D7	4	// GPIOX.BIT7(#104)

//------------------------------------------------------------------------------------------------------------
//
// I2C:
//
//------------------------------------------------------------------------------------------------------------
// ODROID Sensor Board I2C Device IDs
#if 0
const unsigned char i2cDeviceID[] = {
	0x60,	// UV Sensor I2C ID
	0x77	// Pressure Sensor I2C ID
};
#else
const unsigned char i2cDeviceID[] = {
	0x60,	// UV Sensor I2C ID
	0x76	// New Pressure Sensor I2C ID
};
#endif

const unsigned char i2cRegChipID[] = {
	0x00,	// UV Sensor CHIP ID Register
	0xD0	// Pressure Sensor CHIP ID Register
};

// Sensor Count
#define MAX_I2C_CNT	sizeof(i2cDeviceID) / sizeof(i2cDeviceID[0])

const char *i2cHandleNode1 = "/dev/i2c-0";
const char *i2cHandleNode2 = "/dev/i2c-1";

static int i2cHandle1[MAX_I2C_CNT] = { 0, };
static int i2cHandle2[MAX_I2C_CNT] = { 0, };

static int i2cValue1[MAX_I2C_CNT] = { 0, };
static int i2cValue2[MAX_I2C_CNT] = { 0, };

static int i2cPos = 0;

//------------------------------------------------------------------------------------------------------------
//
// Button:
//
//------------------------------------------------------------------------------------------------------------
#define PORT_BUTTON1	5	// GPIOX.BIT5(#102)
#define PORT_BUTTON2	6	// GPIOX.BIT6(#103)

static int btStatus1 = 0;
static int btIrqCnt1 = 0;
static int btStatus2 = 0;
static int btIrqCnt2 = 0;

//------------------------------------------------------------------------------------------------------------
//
// ADC:
//
//------------------------------------------------------------------------------------------------------------
#define PORT_ADC1	0	// ADC.AIN0
#define PORT_ADC2	1	// ADC.AIN1

static int adcValue1 = 0;
static int adcValue2 = 0;

//------------------------------------------------------------------------------------------------------------
//
// Serial:
//
//------------------------------------------------------------------------------------------------------------
#define SERIAL_BAUDRATE	115200

// GPIOX.BIT12(TXD1), GPIOX.BIT13(RXD1)
// ODROID-M1
// const char *serialHandleNode = "/dev/ttyS0";

// ODROID-C4
const char *serialHandleNode = "/dev/ttyS1";

static int  serialHandle = 0;

static unsigned char rxChar = 0;
static unsigned char txChar = 'a';

static unsigned long totalMemSize = 0;
//------------------------------------------------------------------------------------------------------------
//
// LED:
//
//------------------------------------------------------------------------------------------------------------
static int ledPos = 0;

const int ledPorts[] = {
	21,	// GPIOX.BIT4(#101)
	22,	// GPIOX.BIT3(#100)
	23,	// GPIOX.BIT11(#108):PWM_B
	24,	// GPIOX.BIT0(#97)
	11,	// GPIOX.BIT21(#118)
	26,	// GPIOX.BIT2(#99)
	27,	// GPIOX.BIT1(#98)
	13,	// GPIOX.BIT9(#106):MISO
	12,	// GPIOX.BIT10(#107):MOSI/PWM_E
	14,	// GPIOX.BIT8(#105):SCLK
	10,	// GPIOX/BIT20(#117):CE0
};

#define MAX_LED_CNT sizeof(ledPorts) / sizeof(ledPorts[0])

//------------------------------------------------------------------------------------------------------------
//
// Button IRQ Function
//
//------------------------------------------------------------------------------------------------------------
void irq_button1(void)
{
	btIrqCnt1++;
}

void irq_button2(void)
{
	btIrqCnt2++;
}
//------------------------------------------------------------------------------------------------------------
//
// LCD Update Function:
//
//------------------------------------------------------------------------------------------------------------
static void lcd_update (void)
{
	int i, j;

	sprintf(&lcdFb[0][0], "%4d %02X %s %s",
		adcValue1, i2cValue1[i2cPos] & 0xFF, (btStatus1 == 0) ? "DN":"UP", totalMemSize > 4000 ? "-8GB-":"-4GB-");
	sprintf(&lcdFb[1][0], "%4d %02X %s T%c-R%c",
		adcValue2, i2cValue2[i2cPos] & 0xFF, (btStatus2 == 0) ? "DN":"UP", txChar, rxChar);

	for (i = 0; i < LCD_ROW; i++) {
		lcdPosition (lcdHandle, 0, i);
		for(j = 0; j < LCD_COL; j++)
			lcdPutchar(lcdHandle, lcdFb[i][j]);
	}
}

//------------------------------------------------------------------------------------------------------------
//
// system init
//
//------------------------------------------------------------------------------------------------------------
int system_init(void)
{
	int i;

	// LCD Init
	lcdHandle = lcdInit (LCD_ROW, LCD_COL, LCD_BUS,
		PORT_LCD_RS, PORT_LCD_E,
		PORT_LCD_D4, PORT_LCD_D5, PORT_LCD_D6, PORT_LCD_D7, 0, 0, 0, 0);

	if (lcdHandle < 0) {
		fprintf(stderr, "%s : lcdInit failed!\n", __func__);
		return -1;
	}

	// Serial Init
	if ((serialHandle = serialOpen(serialHandleNode, SERIAL_BAUDRATE)) < 0) {
		fprintf(stderr, "%s : Serial failed!\n", __func__);
		return -1;
	}
	serialFlush(serialHandle);

	// I2C Init
	for (i = 0; i < MAX_I2C_CNT; i++) {
		if ((i2cHandle1[i] = wiringPiI2CSetupInterface(i2cHandleNode1, i2cDeviceID[i])) < 0) {
			fprintf(stderr, "%s : I2cSetup1 failed!\n", __func__);
			return -1;
		}

		if ((i2cHandle2[i] = wiringPiI2CSetupInterface(i2cHandleNode2, i2cDeviceID[i])) < 0) {
			fprintf(stderr, " %s : I2cSetup2 failed!\n", __func__);
			return -1;
		}
	}

	// GPIO Init(LED Port ALL Output)
	for (i = 0; i < MAX_LED_CNT; i++) {
		pinMode (ledPorts[i], OUTPUT);
		pullUpDnControl (PORT_BUTTON1, PUD_OFF);
	}

	// Button Pull Up Enable.
	pinMode (PORT_BUTTON1, INPUT);
	pullUpDnControl (PORT_BUTTON1, PUD_UP);
	if ( wiringPiISR (PORT_BUTTON1, INT_EDGE_FALLING, &irq_button1) < 0 ) {
		fprintf (stderr, "Unable to setup ISR: %s\n", strerror (errno));
		return -1;
	}

	pinMode (PORT_BUTTON2, INPUT);
	pullUpDnControl (PORT_BUTTON2, PUD_UP);
	if ( wiringPiISR (PORT_BUTTON2, INT_EDGE_FALLING, &irq_button2) < 0 ) {
		fprintf (stderr, "Unable to setup ISR: %s\n", strerror (errno));
		return -1;
	}
	return 0;
 }

//------------------------------------------------------------------------------------------------------------
//
// board date get
//
//------------------------------------------------------------------------------------------------------------
void boardGetData(void)
{
	static int flag = 0;
	int i;

	//  LED Control
	for(i = 0; i < MAX_LED_CNT; i++)
		digitalWrite (ledPorts[i], 0); // LCD All Clear

	if (flag) {
		for(i = 1; i < MAX_LED_CNT; i += 2)
			digitalWrite (ledPorts[i], 1);
		flag = 0;
	}
	else {
		for(i = 0; i < MAX_LED_CNT; i += 2)
			digitalWrite (ledPorts[i], 1);
		flag = 1;
	}

	if(ledPos >= MAX_LED_CNT) ledPos = 0;

	// adc value read
	adcValue1 = analogRead (PORT_ADC1);
	adcValue2 = analogRead (PORT_ADC2);

	// button status read
	btStatus1 = digitalRead (PORT_BUTTON1);
	btStatus2 = digitalRead (PORT_BUTTON2);

	// i2c read
	i2cPos = i2cPos ? 0 : 1;

	i2cValue1[i2cPos] = wiringPiI2CReadReg8 (i2cHandle1[i2cPos], i2cRegChipID[i2cPos]);
	i2cValue2[i2cPos] = wiringPiI2CReadReg8 (i2cHandle2[i2cPos], i2cRegChipID[i2cPos]);

	// serial tx set
	if(++txChar >= 'z')   txChar = 'a';
	serialPutchar(serialHandle, txChar);

	// serial rx get
	//if (serialDataAvail(serialHandle)) {
		rxChar = serialGetchar(serialHandle);
	//};
	serialFlush(serialHandle);

	// stdout(console) display
	fprintf(stdout, "- ADC1 = %d, ADC2 = %d, I2C1 = %d, I2C2 = %d, BT1 = %s, BT2 = %s, TX = %c, RX = %c \r",
		adcValue1, adcValue2, i2cValue1[i2cPos], i2cValue2[i2cPos],
		btStatus1 ? "Release":"Press", btStatus2 ? "Release":"Press", txChar, rxChar);
	fprintf(stdout, "- BT1 IRQ = %d, BT2 IRQ = %d\n\n", btIrqCnt1, btIrqCnt2);
	fflush(stdout);
}

//------------------------------------------------------------------------------------------------------------
unsigned long getTotalMemorySize(void)
{
	struct sysinfo info;
	sysinfo(&info);
	fprintf(stdout, "uptime     : %ld\n", info.uptime);
	fprintf(stdout, "total ram  : %ld\n", info.totalram);
	fprintf(stdout, "free ram   : %ld\n", info.freeram);
	fprintf(stdout, "shared ram : %ld\n", info.sharedram);
	fprintf(stdout, "buffer ram : %ld\n", info.bufferram);
	fprintf(stdout, "free swap  : %ld\n", info.freeswap);
	return info.totalram;
}
//------------------------------------------------------------------------------------------------------------
//
// Start Program
//
//------------------------------------------------------------------------------------------------------------
int main (int argc, char *argv[])
{
	static int timer = 0 ;

	wiringPiSetup ();

	if (system_init() < 0)
	{
		fprintf (stderr, "%s: System Init failed\n", __func__);
		return -1;
	}

	totalMemSize = getTotalMemorySize() / (1024*1024);

	for(;;) {
		if (millis () < timer)
			continue ;
		timer = millis () + LCD_UPDATE_PERIOD;

		// All Data update
		boardGetData();
		lcd_update();
	}

	return 0;
}

//------------------------------------------------------------------------------------------------------------
//------------------------------------------------------------------------------------------------------------

