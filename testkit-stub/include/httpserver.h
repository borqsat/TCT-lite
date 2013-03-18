#include <stdio.h>
#include <string.h>
#include "testcase.h"

#include <string>
using namespace std;

void timer_handler(int signum);

typedef struct HttpRequest
{
    string method;    // request type
    string path;         // request path
    string content;      // request content
    int  contentlength; // length of request length
    int  contenttype;   // response content type
    int  rangeflag;     // below three are for send if disconnect. they are start, end and total length of a disconnected file.
    long rangestart;
    long rangeend;
    long rangetotal;
    string prefix;
    int  responsecode;  //response code
} HR;

class HttpServer
{
public:
    HttpServer();
    virtual ~HttpServer();
public:
    void StartUp();   
    void processpost(int s,struct HttpRequest *prequest);
    void sendresponse(int s,int code,struct HttpRequest *prequest, string content);
    int sendsegment(int s, string buffer);
    void parse_json_str(string jsonstr);
    int getrequest(string requestbuf,struct HttpRequest *prequest);
    bool get_auto_case(string content,string *type);
    void checkResult(TestCase* testcase);
    void killAllWidget();
    void start_client(string cmd);

    void find_purpose(struct HttpRequest *prequest, bool auto_test);
    void getCurrentTime();
    void cancel_time_check();
    void set_timer();
    struct sigaction sa;
    struct itimerval timer ;
    char m_str_time[32];
    int gIsRun;
    int clientsocket;
    int start_auto_test;
    pid_t client_process_id; 
     
    int gServerStatus;

    //block 
    int m_totalBlocks;
    int m_current_block_index;
    int m_totalcaseCount;
    int m_total_case_index; //current case index in set
    string m_exeType;//auto;manual
    string m_type;
    TestCase *m_test_cases; //the case array

    int m_block_case_index;   //current case index in block
    int m_block_case_count; //case count in every block

    bool m_block_finished;
    bool m_set_finished;

    //TestStatus   
    int m_timeout_count;// continusously time out count

    int m_start_auto_test;
    string m_running_session;
    
    string m_last_auto_result;
    bool m_need_restart_client;


    //some variables get from cmd line
    string g_port;
    string g_hide_status;
    string g_pid_log;
    string g_test_suite;
    string g_exe_sequence;
    string g_client_command;
    string g_enable_memory_collection;
};
