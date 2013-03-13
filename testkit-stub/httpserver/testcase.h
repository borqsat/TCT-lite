#include <stdio.h>
#include <string.h>

#include <signal.h>
#include <sys/time.h>

#include <json-glib/json-glib.h>

class TestCase
{
public:
    TestCase();
    virtual ~TestCase();

public:
    char result[8]; // "pass" or "fail", "block", "N/A"
    char* e_type;
    //string xml_node; // not need now?
    //string xml_name; // not need not?
    char start_at[32];
    char end_at[32];
    char* stdout;
    int timeout;
    bool is_executed;
    int time_task; // what for?

    // below 8 value are sent from Com-module for each case.
    char* order; // case order
    char* case_id;
    char* purpose;
    char* entry;
    char* pre_con;
    char* post_con;
    char* steps;
    char* e_result; // expect result

    int json_len; // the memory needed for this case if store it as json string
    int result_json_len;

    void get_string_value(JsonReader *reader, const char* key, char** value);
    struct sigaction sa;
    struct itimerval timer ;
public:
    void init(char* case_node);// the case_node should be a string in json format
    void print_info_string();
    bool is_manual();
    void to_json(char* str);
    void result_to_json(char* str);
    void set_result(const char* test_result, const char* test_msg, char* end_time);
    void set_start_at(char* start_time, void(*fn)(int));
    void cancel_time_check();

protected:
};
