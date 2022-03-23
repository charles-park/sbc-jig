CC      = gcc
CFLAGS  = -W -Wall -g

INCLUDE = -I/usr/local/include
LDFLAGS = -L/usr/local/lib
LDLIBS  = -lwiringPi -lwiringPiDev -lpthread -lm -lrt -lcrypt

TARGET  = 40pin_test 

SRC_DIRS = .
SRCS     = $(foreach dir, $(SRC_DIRS), $(wildcard $(dir)/*.c))
OBJS     = $(SRCS:.c=.o)

all : $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) $(INCLUDE) -o $@ $^ $(LDFLAGS) $(LDLIBS)

clean :
	rm -f $(OBJS)
	rm -f $(TARGET)
