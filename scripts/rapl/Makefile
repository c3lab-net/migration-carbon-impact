TARGET = rapl-read

all: $(TARGET)

rapl-read: rapl-read.c
	gcc -O2 -Wall -o $(TARGET) rapl-read.c -lm

clean:
	rm -f $(TARGET)

