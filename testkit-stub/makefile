TARGET = httpserver
UT_TARGET = ut
OBJ_PATH = objs
PREFIX_BIN =

CC = g++
INCLUDES = -I include
LIBS = 
CFLAGS =-Wall -Werror
LINKFLAGS = -lpthread

JSON_SRCDIR = src/json
SERVER_SRCDIR = src
MAIN_SRCDIR = src/main
UT_SRCDIR = src/ut

JSON_SOURCES = $(foreach d,$(JSON_SRCDIR),$(wildcard $(d)/*.cpp) )
JSON_OBJS = $(patsubst %.cpp, $(OBJ_PATH)/%.o, $(JSON_SOURCES))

SERVER_SOURCES = $(foreach d,$(SERVER_SRCDIR),$(wildcard $(d)/*.cpp) )
SERVER_OBJS = $(patsubst %.cpp, $(OBJ_PATH)/%.o, $(SERVER_SOURCES))

MAIN_SOURCES = $(foreach d,$(MAIN_SRCDIR),$(wildcard $(d)/*.cpp) )
MAIN_OBJS = $(patsubst %.cpp, $(OBJ_PATH)/%.o, $(MAIN_SOURCES))

UT_SOURCES = $(foreach d,$(UT_SRCDIR),$(wildcard $(d)/*.cpp) )
UT_OBJS = $(patsubst %.cpp, $(OBJ_PATH)/%.o, $(UT_SOURCES))

default:init compile
ut:init ut_compile

$(C_OBJS):$(OBJ_PATH)/%.o:%.c
	$(CC) -c $(CFLAGS) $(INCLUDES) $< -o $@

$(JSON_OBJS):$(OBJ_PATH)/%.o:%.cpp
	$(CC) -c $(CFLAGS) $(INCLUDES) $< -o $@

$(SERVER_OBJS):$(OBJ_PATH)/%.o:%.cpp
	$(CC) -c $(CFLAGS) $(INCLUDES) $< -o $@

$(MAIN_OBJS):$(OBJ_PATH)/%.o:%.cpp
	$(CC) -c $(CFLAGS) $(INCLUDES) $< -o $@

$(UT_OBJS):$(OBJ_PATH)/%.o:%.cpp
	$(CC) -c $(CFLAGS) $(INCLUDES) $< -o $@

init:
	$(foreach d,$(JSON_SRCDIR), mkdir -p $(OBJ_PATH)/$(d);)
	$(foreach d,$(SERVER_SRCDIR), mkdir -p $(OBJ_PATH)/$(d);)
	$(foreach d,$(MAIN_SRCDIR), mkdir -p $(OBJ_PATH)/$(d);)
	$(foreach d,$(UT_SRCDIR), mkdir -p $(OBJ_PATH)/$(d);)

ut_compile:$(JSON_OBJS) $(SERVER_OBJS) $(MAIN_OBJS)
	$(CC)  $^ -o $(UT_TARGET)  $(LINKFLAGS) $(LIBS)

compile:$(JSON_OBJS) $(SERVER_OBJS) $(MAIN_OBJS)
	$(CC)  $^ -o $(TARGET)  $(LINKFLAGS) $(LIBS)

clean:
	rm -rf $(OBJ_PATH)
	rm -f $(TARGET)
	rm -f $(UT_TARGET)

install: $(TARGET)
	#cp $(TARGET) $(PREFIX_BIN)
	install -d $(DESTDIR)/usr/bin/
	install -m 755 $(TARGET) $(DESTDIR)/usr/bin/
	
uninstall:
	rm -f $(PREFIX_BIN)/$(TARGET)

rebuild: clean compile
