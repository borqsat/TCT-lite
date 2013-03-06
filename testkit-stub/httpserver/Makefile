CC=g++

SRC=main.cpp \
    httpserver.cpp \
    testcase.cpp

INCLUDE_H=httpserver.h \
	  testcase.h

HTTPSERVER=httpserver

FLAGS=`pkg-config --cflags glib-2.0 --cflags json-glib-1.0` -ljson-glib-1.0

$(HTTPSERVER) : $(SRC) $(INCLUDE_H)
	$(CC) $(SRC) -o $(HTTPSERVER) $(FLAGS)

.PHONY : clean $(HTTPSERVER)

clean:
	rm $(HTTPSERVER)
