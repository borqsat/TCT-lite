#include <stdio.h>
//#include <sys/socket.h>
////#include <netinet/in.h>
////#include <errno.h>
////#include <netdb.h>
//#include <sys/types.h>
//#include <stdio.h>
//#include <sys/ioctl.h>
//#include <net/if.h>
#include <string.h>
#include "testcase.h"

class HttpServer
{
public:
    HttpServer();
    virtual ~HttpServer();
public:

    void StartUp();
   // static void* processthread(void *para);
    void processpost(int s,struct HttpRequest *prequest);
    void sendresponse(int s,int code,struct HttpRequest *prequest, char* content);
    int sendsegment(int s, char *buffer,int length);
    void parse_json_str(char *jsonstr);
    void get_string_value(JsonReader *reader, const char *key, char **value);
    void init_test(char *content);
    int getrequest(char *requestbuf,struct HttpRequest *prequest);
//    int Send(char* data, int len);
//    int Recv(char* data, int len);
//    int RecvByLine(char* data, int len);
//    BOOL HttpRequestResponse();
//    BOOL Parse(char* data);
//    BOOL Query();
    int gIsRun;
    int clientsocket;
    //int serversocket;
    bool is_finished;
    char session_id[256];

    int start_auto_test;
    pid_t client_process_id;
    char* client_command;
    void checkResult(TestCase* testcase);
    void killAllWidget();
    void start_client(char* cmd);

protected:
    //
//    zfqstring m_hostaddr;
//    unsigned short m_hostport;
//    //
//    zfqstring m_id;
//    zfqstring m_pwd;
//    //
//    zfqstring m_loginid;
//    zfqstring m_loginpwd;
//    //
//    zfqstring m_postdata;
//    zfqstring m_page;
//    DWORD m_method;
//    DWORD m_contentlength;
    //
    //socket m_socket;

     
    int gServerStatus;

    //block   
    int m_totalBlocks;
    int m_currentIndex;
    int m_caseCount;
    char *m_exeType;//auto;muanul
    char *m_type;
    TestCase *m_testcase;

    //TestStatus
    int m_finished;

    char *m_suiteName;
    char *m_setName;

    //TestResult
    //int m_caseCount;

};
