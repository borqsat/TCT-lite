#include <stdio.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <errno.h>
#include <netdb.h>
#include <sys/types.h>
#include <stdio.h>
#include <errno.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <netinet/ip.h>
#include <netinet/in.h>
#include <string.h>
#include <arpa/inet.h>
#include <netinet/tcp.h>
#include <pthread.h>
#include <signal.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>

#include <glib-object.h>
#include <json-glib/json-glib.h>

#include "httpserver.h"

#define SERVER_PORT 8080
#define MAX_BUF 8192

#define GET_COMMON   0
#define GET_CGI   1
#define HEAD   2
#define POST   3
#define TRACR  4
#define BAD_REQUEST -1

HttpServer::HttpServer()
{
        is_finished = false;
        m_exeType = NULL;//auto;muanul
        m_type = NULL;
        m_suiteName = NULL;
        m_setName = NULL;
    }

HttpServer::~HttpServer()
{
    if(m_exeType)
    {
        delete []m_exeType;
        m_exeType = NULL;

    }
     if(m_type)
    {
        delete []m_type;
        m_type = NULL;

    }
     if(m_suiteName)
    {
        delete []m_suiteName;
        m_suiteName = NULL;

    }
     if(m_setName)
    {
        delete []m_setName;
        m_setName = NULL;

    }
    
}

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

int HttpServer::sendsegment(int s, char *buffer,int length)
{
        if(length <= 0)
                return 0;
        printf("%s\n",buffer);
        int result = send(s,buffer,length,0);
        if(result < 0)
                return 0;
        return 1;
}

// generate response code. send response
void HttpServer::sendresponse(int s, int code, struct HttpRequest *prequest, char* content)
{
        char buffer[2048];
        char contenttype[200];

        prequest->responsecode = code;
        // generate response head
        switch(code)
        {
        case 200:
                sprintf(buffer,
                        "HTTP/1.1 200 OK\r\n"
                        "Server: Server/1.0\r\n"
                        "Content-Type: %s\r\n"
                        "Accept-Ranges: bytes\r\n"
                        "Content-Length: %d\r\n"
                        "Connection: close\r\n"
                        "Access-Control-Allow-Origin: *\r\n"
                        "\r\n"
                        "%s", prequest->prefix, strlen(content), content);
                break;
        case 404:
                strcpy(content,"<html><head><title>Object Not Found</title></head><body><h1>Object Not Found</h1>File Not Found.</body></html>");
                sprintf(buffer,
                        "HTTP/1.1 404 Object Not Found\r\n"
                        "Server: Server/1.0\r\n"
                        "Content-Type: %s\r\n"
                        "Content-Length: %d\r\n"
                        "Connection: close\r\n"
                        "\r\n"
                        "%s", prequest->prefix, strlen(content), content);
                break;
        case 505:
                break;
        default:
                break;
        }
        sendsegment(s,buffer,strlen(buffer));
}

int HttpServer::getrequest(char *requestbuf,struct HttpRequest *prequest)
{

        char protocol[20];
        char path[200];
        int i = 0;
        if(sscanf(requestbuf, "%s %s %s", prequest->method, path, protocol)!=3)
                return BAD_REQUEST;

        if(strchr(path, '?') == NULL)
        {
                // check whether last character is /. add index.html if it is /
                if(path[strlen(path)-1] == '/')
                        strcat(path,"index.html");
                sprintf(prequest->path,"%s",path);
                // get suffix. set to * if no suffix
                if(sscanf(path, "%s.%s", path, prequest->prefix)!=2)
                        strcpy(prequest->prefix,"*");

                printf("GET path:%s\nprefix:%s\n",prequest->path,prequest->prefix);

                //get the com module send data
                char *s1 = strstr(requestbuf,"\r\n\r\n");
                printf("s1.length %d\n",strlen(s1));
                prequest->content = new char[strlen(s1)+1] ;
                strcpy(prequest->content,s1+4) ;                
                printf("content ================%s\n",prequest->content);
        }
        else
        {
                prequest->content = (char *)malloc(strlen(prequest->path));
                printf("run ?  \n");
                sscanf(prequest->path,"%s?%s",prequest->path, prequest->content);
                printf("run ?  %s|%s \n",prequest->path, prequest->content);
        }

        if(strcmp(prequest->method,"GET") == 0)
        {
            return GET_COMMON;
        }
        else if(strcmp(prequest->method,"POST") == 0)
        {
                return POST;
        }
        return -1;
}


void HttpServer::get_string_value(JsonReader *reader, const char *key, char **value)
{
        json_reader_read_member (reader, key);
        const char* tmp;
        if (key == "cases")
        {
            printf("cases\n");
            bool is_array = json_reader_is_array(reader);
            printf("%d\n",is_array);
            if (is_array == true)
            {
                
                int count = json_reader_count_elements(reader);
                printf("count is %d\n",count);
                m_testcase =  new TestCase[count];                
                
                for (int i = 0; i < count; i++)
                {
                    json_reader_read_element (reader, i);                    
                    json_reader_read_member (reader, "order");
                    m_testcase[i].order = json_reader_get_int_value (reader);
                    json_reader_end_member (reader);
                    printf("m_testcase[i].order is %d\n", m_testcase[i].order);

                    get_string_value(reader, "case_id", &m_testcase[i].case_id);                    
                    printf("m_testcase[i].case_id is %s\n",m_testcase[i].case_id);
                    
                    get_string_value(reader, "purpose", &m_testcase[i].purpose);                    
                    printf("m_testcase[i].purpose is %s\n",m_testcase[i].purpose);

                    /*
                    get_string_value(reader, "test_script_entry", &m_testcase[i].entry);
                    get_string_value(reader, "pre_condition", &m_testcase[i].pre_con);
                    get_string_value(reader, "post_condition", &m_testcase[i].post_con);
                    get_string_value(reader, "step_desc", &m_testcase[i].steps);
                    get_string_value(reader, "expected", &m_testcase[i].e_result);
                    */
                    json_reader_end_element (reader);
                }
            }
            
            //const char* tmp = json_reader_get_array_value (reader);
            /* code */
        }
        else
            tmp = json_reader_get_string_value (reader);
        json_reader_end_member (reader);        
        if (!tmp) return;

        
        *value = new char[strlen(tmp)+1];
        if (!value) return;
        memset(*value, 0, strlen(tmp)+1);
        strcpy(*value, tmp);
        
}
void HttpServer::parse_json_str(char* case_node){
    g_type_init ();
    
    JsonParser *parser = json_parser_new ();
    json_parser_load_from_data (parser, case_node, -1, NULL);

    JsonReader *reader = json_reader_new (json_parser_get_root (parser));
   
    json_reader_read_member (reader, "totalBlk");
    m_totalBlocks = json_reader_get_int_value (reader);
    json_reader_end_member (reader);
    
    json_reader_read_member (reader, "currentBlk");
    m_currentIndex = json_reader_get_int_value (reader);
    json_reader_end_member (reader);

    json_reader_read_member (reader, "casecount");
    m_caseCount = json_reader_get_int_value (reader);
    json_reader_end_member (reader);
    
    //printf("totalBlk is: %d %d\n",m_totalBlocks,m_currentIndex);

    get_string_value(reader, "exetype", &m_exeType);     

    char *case_array;
    get_string_value(reader, "cases", &case_array);

    
    g_object_unref (reader);
    g_object_unref (parser);
}

char* build_json_str(char* key, char* value)
{
        g_type_init ();

        JsonBuilder *builder = json_builder_new ();

        json_builder_begin_object (builder);

        json_builder_set_member_name (builder, key);
        json_builder_add_string_value (builder, value);

        json_builder_end_object (builder);

        JsonGenerator *generator = json_generator_new ();
        JsonNode * root = json_builder_get_root (builder);
        json_generator_set_root (generator, root);
        gchar *str = json_generator_to_data (generator, NULL);
        g_print("%s\n", str);

        json_node_free (root);
        g_object_unref (generator);
        g_object_unref (builder);

        return str;
}

void HttpServer::processpost(int s,struct HttpRequest *prequest)
{

        printf("================%s\n",prequest->path);
        sprintf(prequest->prefix, "%s", "application/json");
        char *json_str;
        char *json_parse_str;
        if (strstr(prequest->path,"/init"))
        {
                     
            printf("[ init the test suit ]\n");
            init_test(prequest->content);            
             
        }
        if(strcmp(prequest->path,"/check_server") == 0)
        {
                printf("[ checking server, and found the server is running ]\n");
                json_str = build_json_str("OK", "1");
        }
        else if(strcmp(prequest->path,"/check_server_status") == 0)
        {
                if (is_finished) json_str = build_json_str("finished", "1");
                else json_str = build_json_str("finished", "0");
        }
        else if(strstr(prequest->path, "/init_session_id"))
        {
                json_str = build_json_str("OK", "1");
                char * para = strchr(prequest->path, '=');
                if (para) {
                        //sscanf(prequest->path, "%*[^=]%s", session_id);
                        sprintf(session_id, "%s", para+1);
                        printf("[ sessionID: %s is gotten from the client ]\n", session_id);
                }
                else printf("[ invalid session id ]\n");
        }
        else if(strcmp(prequest->path,"/shut_down_server") == 0)
        {
                json_str = build_json_str("OK", "1");
                gIsRun = 0;
        }
        else if(strcmp(prequest->path,"/ask_next_step") == 0)
                json_str = build_json_str("step", "continue");


        sendresponse(s, 200, prequest, json_str);
}

void* processthread(void *para)
{
        
        char buffer[1024];
        int iDataNum =0;
        int recvnum=0;
        HttpServer *server = (HttpServer *)para;
        //int clientsocket = *((int *)para);
        //HttpServer *obj = (HttpServer *)para;
        //int clientsocket = obj->clientsocket;
        printf("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<BEGIN [%d]>>>>>>>>>>>>>>>>>>>>>>>\n",server->clientsocket);

        struct HttpRequest httprequest;
        httprequest.content = NULL;
        httprequest.path = NULL;
        httprequest.path = (char *)malloc(1024);
        httprequest.rangeflag = 0;
        httprequest.rangestart = 0;

        while(1)
        {
                
                printf("clinetsocket id is %d\n", server->clientsocket);
                iDataNum = recv(server->clientsocket,buffer+recvnum,sizeof(buffer)-recvnum-1,0);
                if(iDataNum <= 0)
                {
                        close(server->clientsocket);
                        pthread_exit(NULL);
                        return 0;
                }
                recvnum += iDataNum;
                buffer[recvnum]='\0';
                printf("buffer ================%s\n",buffer);               
                
                if(strstr(buffer,"\r\n\r\n")!=NULL || strstr(buffer,"\n\n")!=NULL)
                        break;
        }
        // parse request and process it
        switch(server->getrequest(buffer,&httprequest))
        {
        case GET_COMMON:
        case POST:
                printf("post\n");                
                server->processpost(server->clientsocket,&httprequest);
                break;
        default:
                break;
        }
        //insertlognode(pfilelog,&httprequest);
        if(httprequest.path != NULL)
                free(httprequest.path);
        if(httprequest.content != NULL)
                free(httprequest.content);
        close(server->clientsocket);
        printf("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<END [%d]>>>>>>>>>>>>>>>>>>>>>>>\n",server->clientsocket);
        pthread_exit(NULL);
}
void HttpServer::init_test(char *content){
	printf("init content ================%s\n",content);
    parse_json_str(content);

}

void HttpServer::StartUp()
{
   
    int serversocket;
    gServerStatus = 1;
    struct sockaddr_in server_addr;
    struct sockaddr_in clientAddr;
    int addr_len = sizeof(clientAddr);

    if((serversocket = socket(AF_INET,SOCK_STREAM,0)) < 0)
    {
            perror( "error: create server socket!!!");
            return;
    }

    bzero(&server_addr,sizeof(server_addr));
    server_addr.sin_family =AF_INET;
    server_addr.sin_port = htons(SERVER_PORT);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    if(bind(serversocket,(struct sockaddr *)&server_addr,sizeof(server_addr)) < 0)
    {
            perror("error: bind address !!!!");
            return;
    }

    if(listen(serversocket,5)<0)
    {
            perror("error: listen !!!!");
            return;
    }
    gIsRun = 1;
    printf("Server is running.....\n");
    
    while(gIsRun)
    {
        clientsocket = accept(serversocket,(struct sockaddr *)&clientAddr,(socklen_t*)&addr_len);
        if(clientsocket < 0)
        {
                perror("error: accept client socket !!!");
                continue;
        }
        if(gServerStatus == 0)
        {
                close(clientsocket);
        }
        else if(gServerStatus == 1)
        {
                pthread_t threadid;
                int temp;
               
                temp = pthread_create(&threadid, NULL, processthread, (void *)this);
                /*if(threadid !=0)
                {
                         pthread_join(threadid,NULL);
                }*/
        }
    }
    close(serversocket);
}

void HttpServer::checkResult(TestCase* testcase)
{
    if (!testcase->is_executed) {
        printf("[ Warning: time is out, test case \"%s\" is timeout, set the result to \"BLOCK\", and restart the client ]\n", testcase->purpose);
        //try:
        //    print "[ Warning: time is out, test case \"%s\" is timeout, set the result to \"BLOCK\", and restart the client ]" % case.purpose
        //except Exception, e:
        //    print "[ Warning: time is out, test case \"%s\" is timeout, set the result to \"BLOCK\", and restart the client ]" % str2str(case.purpose)
        //    print "[ Error: found unprintable character in case purpose, error: %s ]\n" % e

        testcase->set_result("BLOCK", "Time is out");
        start_auto_test = 0;
        printf("[ kill existing client, pid: %d ]\n", client_process_id);
        kill(client_process_id, SIGKILL);

        killAllWidget();

        printf("[ start new client in 5sec ]\n");
        sleep(50000);

        start_auto_test = 1;

        start_client(client_command);
    }
    else {
        printf("[ test case \"%s\" is executed in time, and the result is %s ]\n", testcase->purpose, testcase->result);
        //try:
        //    print "[ test case \"%s\" is executed in time, and the result is %s ]" % (case.purpose, case.result)
        //except Exception, e:
        //    print "[ test case \"%s\" is executed in time, and the result is %s ]" % (str2str(case.purpose), str2str(case.result))
        //    print "[ Error: found unprintable character in case purpose, error: %s ]\n" % e
    }
}

void HttpServer::killAllWidget()
{

}

void HttpServer::start_client(char* cmd)
{
        pid_t pid = fork();
        if(pid > 0) client_process_id = pid;
        else if(pid == 0)
        {
                execl("/bin/sh", "sh", "-c", cmd, (char *)0);
        }
        else {
                printf( "[ Error: exception occurs while invoking \"%s\", error: %d ]\n", cmd, pid);
                exit(-1);
        }

    /*try:
        pid_log = TestkitWebAPIServer.default_params["pid_log"]
        proc = subprocess.Popen(command, shell=True)
        if pid_log is not "no_log":
            try:
                with open(pid_log, "a") as fd:
                    pid = str(proc.pid)
                    fd.writelines(pid + '\n')
            except:
                pass
        TestkitWebAPIServer.client_process = proc
        print "[ start client with pid: %s ]\n" % proc.pid
    except Exception, e:
        print "[ Error: exception occurs while invoking \"%s\", error: %s ]\n" % (command, e)
        sys.exit(-1)*/
}