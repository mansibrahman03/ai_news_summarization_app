CC = gcc
CFLAGS = -Wall -Wextra -pthread
TARGET = thread
SRC = thread.c

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC)

clean:
	rm -f $(TARGET)
