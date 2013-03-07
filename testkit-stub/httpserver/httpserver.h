#include <stdio.h>
#include <string.h>
#include "testcase.h"

void timer_handler(int signum);

typedef struct HttpRequest
{
    char method[20];    // request type
    char *path;         // request path
    char *content;      // request content
    int  contentlength; // length of request length
    int  contenttype;   // response content type
    int  rangeflag;     // below three are for send if disconnect. they are start, end and total length of a disconnected file.
    long rangestart;
    long rangeend;
    long rangetotal;
    char prefix[20];
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
    void sendresponse(int s,int code,struct HttpRequest *prequest, char* content);
    int sendsegment(int s, char *buffer,int length);
    void parse_json_str(char *jsonstr);
    void get_string_value(JsonReader *reader, const char *key, char **value);
    int getrequest(char *requestbuf,struct HttpRequest *prequest);
    bool get_auto_case(char *content,char **type);
    void checkResult(TestCase* testcase);
    void killAllWidget();
    void start_client(char* cmd);

    void find_purpose(struct HttpRequest *prequest, bool auto_test);
    void getCurrentTime();
    char m_str_time[32];
//    int Send(char* data, int len);
//    int Recv(char* data, int len);
//    int RecvByLine(char* data, int len);
//    BOOL HttpRequestResponse();
//    BOOL Parse(char* data);
//    BOOL Query();
    int gIsRun;
    int clientsocket;
    //int serversocket;
    //bool is_finished;
    //char session_id[256];
    int start_auto_test;
    pid_t client_process_id; 
     
    int gServerStatus;

    //block   
    char *m_totalBlocks;
    char *m_current_block_index;
    char *m_totalcaseCount_str;
    int m_totalcaseCount;
    int m_total_case_index; //current case index in set
    char *m_exeType;//auto;manual
    char *m_type;
    TestCase *m_test_cases;

    int m_case_index;   //current case index in block
    int m_block_case_count; //case count in every block

    bool m_block_finished;
    bool m_set_finished;

    //TestStatus
    int m_finished;

    //char *m_suiteName;
    //char *m_setName;

    //TestResult
    //int m_caseCount;

    int m_start_auto_test;
    char *m_running_session;
    
    char *m_last_auto_result;
    bool m_need_restart_client;


    //some variables get from cmd line
    char *g_port;
    char *g_hide_status;
    char *g_pid_log;
    char *g_test_suite;
    char *g_exe_sequence;
    char *g_client_command;
    char *g_enable_memory_collection;
};
