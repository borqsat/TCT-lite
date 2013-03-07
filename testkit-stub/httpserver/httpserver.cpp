#include <stdio.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <errno.h>
#include <netdb.h>
#include <sys/types.h>
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

// if use 8080 for SERVER_PORT, it will not work with chrome
#define SERVER_PORT 8000
#define MAX_BUF 8192

#define GET   0
#define HEAD  2
#define POST  3
#define BAD_REQUEST -1

HttpServer::HttpServer()
{
    m_test_cases = NULL;

    //is_finished = false;
    m_exeType = new char[8];
    memset(m_exeType, 0, 8);
    strcpy(m_exeType, "auto");// set default to auto
    m_type = NULL;
    /*m_suiteName = NULL;
    m_setName = NULL;*/
    m_start_auto_test = 1;
    m_totalcaseCount = 0;
    m_case_index = 0;
    m_block_case_count = 0;
    m_last_auto_result = NULL;
    m_need_restart_client = false;
    m_running_session = NULL;
    m_totalBlocks = NULL;
    m_current_block_index = NULL;
    m_totalcaseCount_str = NULL;
    g_port = NULL;
    g_hide_status = NULL;
    g_pid_log = NULL;
    g_test_suite = NULL;
    g_exe_sequence = NULL;
    g_client_command = NULL;
    g_enable_memory_collection = NULL;
    m_block_finished = false;
    m_set_finished = false;
}

HttpServer::~HttpServer()
{
    if (m_test_cases)
    {
        delete []m_test_cases;
        m_test_cases = NULL;
    }

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

    if(m_last_auto_result)
    {
        delete []m_last_auto_result;
        m_last_auto_result = NULL;
    }

    if (m_running_session)
    {
        delete []m_running_session;
        m_running_session = NULL;
    }

    if (m_totalBlocks)
    {
        delete []m_totalBlocks;
        m_totalBlocks = NULL;
    }

    if (m_current_block_index)
    {
        delete []m_current_block_index;
        m_current_block_index = NULL;
    }

    if (m_totalcaseCount_str)
    {
        delete []m_totalcaseCount_str;
        m_totalcaseCount_str = NULL;
    }

    if (g_port)
    {
        delete []g_port;
        g_port = NULL;
    }
    if (g_hide_status)
    {
        delete []g_hide_status;
        g_hide_status = NULL;
    }
    if (g_pid_log)
    {
        delete []g_pid_log;
        g_pid_log = NULL;
    }
    if (g_test_suite)
    {
        delete []g_test_suite;
        g_test_suite = NULL;
    }
    if (g_exe_sequence)
    {
        delete []g_exe_sequence;
        g_exe_sequence = NULL;
    }

    if (g_client_command)
    {
        delete []g_client_command;
        g_client_command = NULL;
    }
    if (g_enable_memory_collection)
    {
        delete []g_enable_memory_collection;
        g_enable_memory_collection = NULL;
    }
}

int HttpServer::sendsegment(int s, char *buffer,int length)
{

    if(length <= 0) return 0;
    printf("%s\n",buffer);
    int result = send(s,buffer,length,0);
    if(result < 0) return 0;
    return 1;
}

// generate response code. send response
void HttpServer::sendresponse(int s, int code, struct HttpRequest *prequest, char *content)
{
    printf("=======content is %s\n", content);
    printf("=======content len is %d\n", strlen(content));
    int len = strlen(content) + 512;
    char* buffer = new char[len];
    memset(buffer,0,len);

    prequest->responsecode = code;
    // generate response head
    switch(code)
    {        
        case 200:{
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
        }
        case 404:{
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
        }
        default:
                break;
    }
    sendsegment(s,buffer,strlen(buffer));
    delete[] buffer;
    buffer = NULL;
}

int HttpServer::getrequest(char *requestbuf,struct HttpRequest *prequest)
{
    char protocol[20];
    char path[200];
    int i = 0;
    if(sscanf(requestbuf, "%s %s %s", prequest->method, path, protocol)!=3)
            return BAD_REQUEST;
    printf("%s\n", requestbuf);

    if(strchr(path, '?') == NULL)
    {
        /*// check whether last character is /. add index.html if it is /
        if(path[strlen(path)-1] == '/')
                strcat(path,"index.html");*/
        sprintf(prequest->path,"%s",path);
        // get suffix. set to * if no suffix
        if(sscanf(path, "%s.%s", path, prequest->prefix)!=2)
                strcpy(prequest->prefix,"*");

        printf("GET path:%s\nprefix:%s\n",prequest->path,prequest->prefix);

        //get the com module send data
        char *s1 = strstr(requestbuf,"\r\n\r\n");
        if (s1)
        {
            printf("s1.length %d\n",strlen(s1));
            printf("s1 %s\n",s1);
            prequest->content = new char[strlen(s1)+1];
            memset(prequest->content,0,strlen(s1)+1);
            strcpy(prequest->content,s1+4);
            //printf("content ================%s\n",prequest->content);
        }
    }
    else 
    {
        sprintf(prequest->path,"%s",path);
        prequest->content = (char *)malloc(strlen(path));
        printf("get path ================%s\n",path);
        strcpy(prequest->content,strstr(path,"?")+1);
        //sscanf(path,"%s?%s",prequest->path, prequest->content);
        printf("get content %s\n",prequest->content);
    }
    if(strcmp(prequest->method,"GET") == 0)
    {
        return GET;
    }
    else if(strcmp(prequest->method,"POST") == 0)
    {
        return POST;
    }
    return -1;
}


void HttpServer::get_string_value(JsonReader *reader, const char *key, char **value)
{
    printf("key is %s\n",key);
    bool key_exist = json_reader_read_member (reader, key);
    if (key_exist == false)
        return;

    const char* tmp;
    if (strcmp(key ,"cases") == 0)
    {
        bool is_array = json_reader_is_array(reader);
        printf("%d\n",is_array);
        if (is_array == true)
        {
            m_block_case_count = json_reader_count_elements(reader);
            printf("block case count is %d\n",m_block_case_count);
            if (m_test_cases)
            {
                delete []m_test_cases;// core dump with this?
                m_test_cases = NULL;
            }
            m_test_cases = new TestCase[m_block_case_count];
            for (int i = 0; i < m_block_case_count; i++)
            {
                json_reader_read_element (reader, i);
                m_test_cases[i].json_len = strlen("{");

                get_string_value(reader, "order", &m_test_cases[i].order);
                if (m_test_cases[i].order ){
                    m_test_cases[i].json_len += strlen("\"order\":\"") + strlen(m_test_cases[i].order) + strlen("\",");
                    printf("m_test_cases[i].order is %s\n", m_test_cases[i].order);
                }

                get_string_value(reader, "case_id", &m_test_cases[i].case_id);
                if (m_test_cases[i].case_id )
                {
                    m_test_cases[i].json_len += strlen("\"case_id\":\"") + strlen(m_test_cases[i].case_id) + strlen("\",");
                    printf("m_test_cases[i].case_id is %s\n",m_test_cases[i].case_id); 
                }
                
                get_string_value(reader, "purpose", &m_test_cases[i].purpose);
                if (m_test_cases[i].purpose )
                {
                    m_test_cases[i].json_len += strlen("\"purpose\":\"") + strlen(m_test_cases[i].purpose) + strlen("\",");
                    printf("m_test_cases[i].purpose is %s\n",m_test_cases[i].purpose);
                }

                
                get_string_value(reader, "test_script_entry", &m_test_cases[i].entry);                
                if (m_test_cases[i].entry )
                    m_test_cases[i].json_len += strlen("\"test_script_entry\":\"") + strlen(m_test_cases[i].entry) + strlen("\",");
                
                get_string_value(reader, "pre_condition", &m_test_cases[i].pre_con);
                if (m_test_cases[i].pre_con)
                    m_test_cases[i].json_len += strlen("\"pre_condition\":\"") + strlen(m_test_cases[i].pre_con) + strlen("\",");
                
                get_string_value(reader, "post_condition", &m_test_cases[i].post_con);
                if (m_test_cases[i].post_con)
                    m_test_cases[i].json_len += strlen("\"post_condition\":\"") + strlen(m_test_cases[i].post_con) + strlen("\",");
                
                get_string_value(reader, "step_desc", &m_test_cases[i].steps);
                if (m_test_cases[i].steps)
                    m_test_cases[i].json_len += strlen("\"step_desc\":\"") + strlen(m_test_cases[i].steps) + strlen("\",");
                
                get_string_value(reader, "expected", &m_test_cases[i].e_result);
                if (m_test_cases[i].e_result)
                    m_test_cases[i].json_len += strlen("\"expected\":\"") + strlen(m_test_cases[i].e_result) + strlen("\"}");
                json_reader_end_element (reader);
            }
        }
        return;
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

void HttpServer::parse_json_str(char* case_node)
{
    g_type_init ();
    
    JsonParser *parser = json_parser_new ();
    json_parser_load_from_data (parser, case_node, -1, NULL);

    JsonReader *reader = json_reader_new (json_parser_get_root (parser));
   
    get_string_value(reader, "totalBlk", &m_totalBlocks); 
    get_string_value(reader, "currentBlk", &m_current_block_index);     
    get_string_value(reader, "casecount", &m_totalcaseCount_str);
    //printf("m_totalcaseCount_str %s\n",m_totalcaseCount_str); 
    if (m_totalcaseCount_str)
    {
        m_totalcaseCount = atoi(m_totalcaseCount_str);
    }
    //printf("m_totalcaseCount %d\n",m_totalcaseCount); 
    get_string_value(reader, "exetype", &m_exeType);   
    //printf("m_totalBlocks m_current_block_index m_totalcaseCount m_exeType is: %s %s %d %s\n",m_totalBlocks,m_current_block_index,m_totalcaseCount,m_exeType);  

    char *case_array;
    get_string_value(reader, "cases", &case_array);
    g_object_unref (reader);
    g_object_unref (parser);
}

char* build_json_str(char **key, char **value,int len)
{
    g_type_init ();

    JsonBuilder *builder = json_builder_new ();
    json_builder_begin_object (builder);
    
    for (int i = 0; i < len; ++i)
    {
        json_builder_set_member_name (builder, key[i]);
        json_builder_add_string_value (builder, value[i]);
    }

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
void copy_const_str(char **to_str,const char *from_str)
{
    *to_str = new char[strlen(from_str)+1];
    memset(*to_str,0,strlen(from_str)+1);
    strcpy(*to_str,from_str);
}

void HttpServer::processpost(int s,struct HttpRequest *prequest)
{

    printf("================%s\n",prequest->path);
    sprintf(prequest->prefix, "%s", "application/json");
    char *json_str = NULL;
    char *json_parse_str = NULL;
    if (strstr(prequest->path,"/init_test"))
    {
        printf("[ init the test suit ]\n");
        parse_json_str(prequest->content);
        if (strcmp(m_current_block_index, "1") == 0)//the first block,start client
        {
            if (g_client_command)
                start_client(g_client_command);
            else
                printf("no g_client_command\n");
            m_total_case_index = 0;
        }  
        else
            m_case_index = 0;

        const char *tmp = "{\"OK\":1}";
        copy_const_str(&json_str,tmp);
        printf("json_str is %s\n", json_str);        
    }
    else if(strcmp(prequest->path,"/check_server") == 0)
    {
        printf("[ checking server, and found the server is running ]\n");
        const char *tmp = "{\"OK\":1}";
        copy_const_str(&json_str,tmp);
    }
    else if(strcmp(prequest->path,"/check_server_status") == 0)
    {
        const char *tmp = NULL;
        if (m_set_finished == true) 
            tmp = "{\"finished\":1}";
        else{
            if (m_block_finished == true)
                tmp = "{\"finished\":0,\"block_finished\":1}";
            else
                tmp = "{\"finished\":0,\"block_finished\":0}";
        }            

        copy_const_str(&json_str,tmp);
    }
    else if(strstr(prequest->path, "/init_session_id"))
    { 
        const char *tmp = "{\"OK\":1}";
        copy_const_str(&json_str,tmp);

        char * para = strchr(prequest->path, '=');
        if (para) {
                //sscanf(prequest->path, "%*[^=]%s", session_id);
                m_running_session = new char[strlen(para)+1];
                memset(m_running_session,0,strlen(para)+1);
                sprintf(m_running_session, "%s", para+1);
                printf("[ sessionID: %s is gotten from the client ]\n", m_running_session);
        }
        else printf("[ invalid session id ]\n");
        // printf("init end the path:================%s\n",prequest->path);
    }
    else if(strcmp(prequest->path,"/shut_down_server") == 0)
    {
        const char *tmp = "{\"OK\":1}";
        copy_const_str(&json_str,tmp);
        gIsRun = 0;
    }
    else if(strcmp(prequest->path,"/ask_next_step") == 0)
    {
        const char *tmp = "{\"step\":\"continue\"}";
        copy_const_str(&json_str,tmp);
    }
    else if(strstr(prequest->path,"/auto_test_task"))
    {
        if (!m_test_cases)
        {
            const char *tmp = "{\"OK\":\"no case\"}";
            copy_const_str(&json_str,tmp);
            sendresponse(s, 200, prequest, json_str);
            delete[] json_str;
            return;
        }
        else if (strcmp(m_exeType, "auto") != 0)
        {
            copy_const_str(&json_str, "{\"OK\":\"no auto case\"}");
            sendresponse(s, 200, prequest, json_str);
            delete[] json_str;
            return;
        }

        char *type = new char[16];
        memset(type,0,sizeof(char)*16);

        bool find_tc = get_auto_case(prequest->content,&type);
        if (find_tc == false)
        {
            if(strlen(type) > 0)
			{
                char tmpstr[32];
                sprintf(tmpstr, "{\"%s\":\"0\"}", type);
                sendresponse(s, 200, prequest, tmpstr);
                delete []type;
                return;
            }
        }
        else{
            delete []type;
            char* tmpstr = new char[m_test_cases[m_case_index].json_len+128];
            memset(tmpstr,0,m_test_cases[m_case_index].json_len+128);
			if (!tmpstr)
            {
                const char *tmp = "fail to allocate memory";
                copy_const_str(&json_str,tmp);
            }
            else
            {
                printf("send case: m_case_index is %d\n",m_case_index);
                m_test_cases[m_case_index].to_json(tmpstr);
                sendresponse(s, 200, prequest, tmpstr);   
                //m_case_index++;
				//m_total_case_index++;
                if (tmpstr)
                {
                   delete[] tmpstr;
                   tmpstr = NULL;
                }               
                return;
            }
        }
    }
    else if(strstr(prequest->path,"/manual_cases"))
    {
        if (!m_test_cases)
        {
            const char *tmp = "{\"OK\":\"no case\"}";
            copy_const_str(&json_str,tmp);
        }
        else if (strcmp(m_exeType, "auto") == 0)
        {
            copy_const_str(&json_str, "{\"OK\":\"no manual case\"}");
        }
        else
        {
            int length = 0;
            for (int i = 0; i < m_block_case_count; i++) length += m_test_cases[i].json_len + strlen(",");

            char* str = new char[length+128];
            if (!str)
            {
                const char *tmp = "fail to allocate memory";
                copy_const_str(&json_str,tmp);
            }
            else 
            {
                memset(str, 0, length+1);
                char* point = str + 1;

                str[0] = '[';
                for (int i = 0; i < m_block_case_count; i++)
                {
                    m_test_cases[i].to_json(point);
                    point = str + strlen(str);
                    point[0] = ',';
                    point += 1;
                }
                str[strlen(str)-1] = ']';

                sendresponse(s, 200, prequest, str);
                delete[] str;
            }
        }
    }
    else if(strstr(prequest->path,"/case_time_out"))
    {
        if (!m_test_cases)
        {
            const char *tmp = "{\"OK\":\"no case\"}";
            copy_const_str(&json_str,tmp);
        }
        else
        {
            m_test_cases[m_case_index].cancel_time_check();
            checkResult(&m_test_cases[m_case_index]);

            const char *tmp = "{\"OK\":\"timeout\"}";
            copy_const_str(&json_str,tmp);
        }
    }
    else if(strstr(prequest->path,"/commit_manual_result"))
    {
        if ((strlen(prequest->content) == 0) || (!m_test_cases))
        {
            const char *tmp = "{\"OK\":\"no case\"}";
            copy_const_str(&json_str,tmp);
        } 
        else
        {
            find_purpose(prequest, false);
            const char *tmp = "{\"OK\":1}";
            copy_const_str(&json_str,tmp);
        }
        m_set_finished = true;
    }
	else if(strstr(prequest->path,"/check_execution_progress"))
    {
        char *tmpstr = new char[128];
        memset(tmpstr,0,128);
        sprintf(tmpstr,"{\"Total\":%d,\"Current\":%d,\"Last Case Result\":\"%s\"}",m_totalcaseCount,m_total_case_index,m_last_auto_result);
        printf("Total: %d, Current: %d\nLast Case Result: %s" ,m_totalcaseCount, m_total_case_index, m_last_auto_result);
        sendresponse(s, 200, prequest, tmpstr);
		delete []tmpstr;

        if (m_last_auto_result == NULL)
            m_last_auto_result = new char[32];
        memset(m_last_auto_result,0,32);
        strcpy(m_last_auto_result,"BLOCK");
        
        return;
    }
    else if(strcmp(prequest->path,"/generate_xml") == 0)
    {
        if (!m_test_cases)
        {
            const char *tmp = "{\"OK\":\"no case\"}";
            copy_const_str(&json_str,tmp);
        } 
        else
        {
            char* str = new char[256*m_block_case_count];
            if (!str)
            {
                const char *tmp = "fail to allocate memory";
                copy_const_str(&json_str,tmp);
            }
            else
            {
                memset(str, 0, 256*m_block_case_count);
                char* point = str;

                sprintf(str, "{\"count\":\"%d\",\"cases\":[", m_block_case_count);
                point += strlen(str);
                for (int i = 0; i < m_block_case_count; i++)
                {
                    m_test_cases[i].result_to_json(point);
                    point += m_test_cases[i].result_json_len;
                    point[0] = ',';
                    point += 1;
                }
                str[strlen(str)-1] = ']';
                str[strlen(str)] = '}';

                sendresponse(s, 200, prequest, str);
                delete[] str;
            }
        }
    }

    else if (strcmp(prequest->path,"/commit_result") == 0)//for auto case
    {
        if (!m_test_cases) 
        {
            const char *tmp = "{\"OK\":\"no case\"}";
            copy_const_str(&json_str,tmp);
            sendresponse(s, 200, prequest, json_str);
            return;
        }
        m_case_index++;
        m_total_case_index++;

        find_purpose(prequest, true);

        const char *tmp = "{\"OK\":1}";
        copy_const_str(&json_str,tmp);

        if (m_case_index < m_block_case_count)
            m_block_finished = false;
        else
            m_block_finished = true;
        if (m_total_case_index < m_totalcaseCount)
            m_set_finished = false;
        else
            m_set_finished = true;


        if(m_need_restart_client == true)
        {
            sendresponse(s, 200, prequest, json_str);
            // kill client
            m_start_auto_test = 0;
           
            printf("[ kill existing client, pid: %d  to release memory ]\n", client_process_id);
            kill(client_process_id, SIGKILL);
            killAllWidget();

            printf("[ start new client in 5sec ]\n");
            sleep(50000);
            m_start_auto_test = 1;
            m_need_restart_client = 0;
            start_client(g_client_command);
            return;
        }
    }

    if (json_str != NULL)
    {
        sendresponse(s, 200, prequest, json_str);
        delete []json_str;
        json_str = NULL;
    }
}

void HttpServer::find_purpose(struct HttpRequest *prequest, bool auto_test)
{
            printf("=============content: %s, len: %d\n", prequest->content, strlen(prequest->content));

            char* purpose = NULL;
            char* result = NULL;
            char* msg = NULL;

            char *content = new char[strlen(prequest->content)+1];
            memset(content, 0, strlen(prequest->content)+1);
            char* tmp = content;
            strcpy(content, prequest->content);// must copy the content to a local variable, otherwise segment fault?
            while (content != NULL) {
                char* pair = strsep(&content, "&");
                char* key = strsep(&pair, "=");
                if (strcmp(key, "purpose") == 0) 
                {
                    purpose = new char[strlen(pair) + 1];
                    strcpy(purpose, pair);
                }
                else if (strcmp(key, "result") == 0) 
                {
                    result = new char[strlen(pair) + 1];
                    strcpy(result, pair);
                }
                else if (strcmp(key, "msg") == 0) 
                {
                    msg = new char[strlen(pair) + 1];
                    strcpy(msg, pair);
                    getCurrentTime();
                }
            }
            delete[] tmp;

            for (int i = 0; i < m_block_case_count; i++)
            {
                if (strcmp(m_test_cases[i].purpose, purpose) == 0)
                {
                    m_test_cases[i].set_result(result, msg, m_str_time);
                }
            }

            if (auto_test)
            {
                if (m_last_auto_result == NULL)
                    m_last_auto_result = new char[32];
                memset(m_last_auto_result,0,32);
                strcpy(m_last_auto_result, result);
            }

            if (purpose != NULL) delete[] purpose;
            if (result != NULL) delete[] result;
            if (msg != NULL) delete[] msg;
}

void* processthread(void *para)
{
    char buffer[102400]; // suppose 1 case need 1k, 100 cases will be sent each time, we need 100k memory?
    long iDataNum =0;
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
        printf("iDataNum is %ld\n", iDataNum);
        if(iDataNum <= 0)
        {
                close(server->clientsocket);
                pthread_exit(NULL);
                return 0;
        }
        recvnum += iDataNum;
        buffer[recvnum]='\0';
        printf("buffer is ================%s\n",buffer);               
        
        if(strstr(buffer,"\r\n\r\n")!=NULL || strstr(buffer,"\n\n")!=NULL)
                break;
    }
    // parse request and process it
    switch(server->getrequest(buffer,&httprequest))
    {
    case GET:
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

void timer_handler(int signum)
{    
    printf("time out \n");
    // when timeout, we send a http request to server, so server can check result. no other convinent way to do it?
    const char *strings="GET /case_time_out HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: Close\r\n\r\n";
    int sockfd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in address;
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = inet_addr("127.0.0.1");
    address.sin_port = htons(SERVER_PORT);
    int len = sizeof(address);
    int result = connect(sockfd,  (struct sockaddr *)&address, len);
    if(result == -1){
        printf("fail to send timeout request to server!\n");
    }
    else 
    {
        write(sockfd, strings, strlen(strings));
        printf("%s\n", strings);
        //char ch;
        //while(read(sockfd, &ch, 1)) printf("%c", ch);
        close(sockfd);    
        printf("finish send timeout cmd\n");//report error: accept client socket !!!: Interrupted system call?
    }
}

void HttpServer::getCurrentTime()
{
        memset(m_str_time,0,32);
        time_t timer; 
        struct tm* t_tm; 
        time(&timer); 
        t_tm = localtime(&timer); 
        sprintf(m_str_time,"%4d-%02d-%02d %02d:%02d:%02d", t_tm->tm_year+1900, 
        t_tm->tm_mon+1, t_tm->tm_mday, t_tm->tm_hour, t_tm->tm_min, t_tm->tm_sec); 
}

bool HttpServer::get_auto_case(char *content,char **type)
{
    if(m_start_auto_test){
        if (content != NULL)
        {
            char *value;
            printf("content is %s\n", content);
            value = strstr(content,"=");
            //sscanf(content,"%s=%s",key,value);
            if (value)
            {
                printf("value is %s\n", value+1);
                if (strcmp(m_running_session, value+1) == 0)
                {
                    //do the test
                    //printf("session id ==\n");                
                    if (m_case_index < m_block_case_count){
                        getCurrentTime();
                        m_test_cases[m_case_index].set_start_at(m_str_time, timer_handler);
                        return true;
                    }
                    else{
                        printf ("\n[ no auto case is available any more ]");
                        strcpy(*type,"none");
                    }
                }
                else
                {
                   //sprint ("[ sessionID: %s in auto_test_task(), on server side, the ID is %s ]" % (parsed_query['session_id'][0], TestkitWebAPIServer.running_session_id));
                   printf ("[ Error: invalid session ID ]\n");
                   strcpy(*type,"invalid");
                }
            }
        }
    }
    else
    {
        printf ("\n[ restart client process is activated, exit current client ]");        
        strcpy(*type,"stop");
    }
    return false;
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
                //must have,otherwise the thread can not exit
                if(threadid !=0)
                {
                    pthread_join(threadid,NULL);
                }
        }        
    }
    close(serversocket);
}

void HttpServer::checkResult(TestCase* testcase)
{
    printf("%d\n", testcase->is_executed);
    if (!testcase->is_executed) {
        printf("[ Warning: time is out, test case \"%s\" is timeout, set the result to \"BLOCK\", and restart the client ]\n", testcase->purpose);
        //try:
        //    print "[ Warning: time is out, test case \"%s\" is timeout, set the result to \"BLOCK\", and restart the client ]" % case.purpose
        //except Exception, e:
        //    print "[ Warning: time is out, test case \"%s\" is timeout, set the result to \"BLOCK\", and restart the client ]" % str2str(case.purpose)
        //    print "[ Error: found unprintable character in case purpose, error: %s ]\n" % e

        getCurrentTime();
        testcase->set_result("BLOCK", "Time is out", m_str_time);
        m_start_auto_test = 0;
        printf("[ kill existing client, pid: %d ]\n", client_process_id);
        kill(client_process_id, SIGKILL);

        killAllWidget();

        printf("[ start new client in 5sec ]\n");
        sleep(5);

        m_start_auto_test = 1;

        start_client(g_client_command);
    }
    else {
        m_case_index++;
        m_total_case_index++;
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
    system("echo 3 > /proc/sys/vm/drop_caches");// what for?
    //system("kill -9 ` ps -ef | grep wrt-launcher | grep -v grep |  awk '{printf $2};{printf \" \"}'`");

    char buf[128];
    memset(buf, 0, 128);
    char cmd[256];
    FILE *pp;
    if( (pp = popen("wrt-launcher -l | awk '{print $NF}' | sed -n '3,$p'", "r")) == NULL )
    {
        printf("popen() error!\n");
        return;
    }

    while(fgets(buf, sizeof buf, pp))
    {
        printf("%s", buf);
        buf[strlen(buf)-1] = 0; // remove the character return at the end.

        memset(cmd, 0, 256);
        sprintf(cmd, "kill -9 `ps -ef | grep %s | grep -v grep | awk '{printf $2};{printf \" \"}'`\n", buf);
        printf("%s", cmd);
        system(cmd);
        memset(buf, 0, 128);
    }
    pclose(pp);

    /*OS = platform.system()
    if OS == "Linux":
        # release memory in the cache
        fi_c, fo_c, fe_c = os.popen3("echo 3 > /proc/sys/vm/drop_caches")
        # kill widget
        fi, fo, fe = os.popen3("wrt-launcher -l")
        for line in fo.readlines():
            package_id = "none"
            pattern = re.compile('\s+([a-zA-Z0-9]*?)\s*$')
            match = pattern.search(line)
            if match:
                package_id = match.group(1)
            if package_id != "none":
                pid_cmd = "ps aux | grep %s | sed -n '1,1p'" % package_id
                fi_pid, fo_pid, fe_pid = os.popen3(pid_cmd)
                for line_pid in fo_pid.readlines():
                    pattern_pid = re.compile('app\s*(\d+)\s*')
                    match_pid = pattern_pid.search(line_pid)
                    if match_pid:
                        widget_pid = match_pid.group(1)
                        print "[ kill existing widget, pid: %s ]" % widget_pid
                        killall(widget_pid)*/
}

void HttpServer::start_client(char* cmd)
{
    printf("%s\n", cmd);

    pid_t pid = fork();
    if(pid > 0) 
    {
            printf("parent %d\n", pid);
            client_process_id = pid;
    }
    else if(pid == 0)
    {
            printf("now start\n");
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
