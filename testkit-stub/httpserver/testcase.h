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
    char* purpose;
    char* entry;
    char* e_result; // expect result
    char result[8]; // "pass" or "fail", "block", "N/A"
    char* msg;
    char* e_type;
    //string xml_node; // not need now?
    //string xml_name; // not need not?
    int start_at;
    int end_at;
    int timeout;
    bool is_executed;
    int time_task; // what for?
    int order; // case order
    char* case_id;
    char* pre_con;
    char* post_con;
    char* steps;

    void get_string_value(JsonReader *reader, const char* key, char** value);
    struct sigaction sa;
    struct itimerval timer ;
public:
    void init(char* case_node);// the case_node should be a string in json format
    void print_info_string();
    bool is_manual();
    void to_json(char* str);
    //string get_xml_name();
    //void to_xml_node();
    void set_result(char* test_result, char* test_msg);
    void set_start_at(int start_at, void(*fn)(int));
    void cancel_time_check();

protected:
};
