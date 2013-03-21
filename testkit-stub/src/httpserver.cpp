#include <stdio.h>
#include <sys/socket.h>
#include <netinet/in.h>
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

#include <json/json.h>
#include "comfun.h"
#include "httpserver.h"

// if use 8080 for SERVER_PORT, it will not work with chrome
#define SERVER_PORT 8000
#define MAX_BUF 102400

#define GET   0
#define HEAD  2
#define POST  3
#define BAD_REQUEST -1

//#define DEBUG

HttpServer::HttpServer()
{
    m_test_cases = NULL;
    m_exeType = "auto";// set default to auto
    m_type = "";    
    m_start_auto_test = 1;
    m_totalcaseCount = 0;
    m_block_case_index = 0;
    m_block_case_count = 0;
    m_last_auto_result = "N/A";
    m_need_restart_client = false;
    m_running_session = "";
    g_port = "";
    g_hide_status = "";
    g_pid_log = "";
    g_test_suite = "";
    g_exe_sequence = "";
    g_enable_memory_collection = "";
    m_block_finished = false;
    m_set_finished = false;
    m_timeout_count = 0;
    m_failto_launch = 0;

    memset ( &sa, 0, sizeof ( sa ) ) ;
    sa.sa_handler = timer_handler;
    sigaction ( SIGALRM, &sa, NULL );
}

HttpServer::~HttpServer()
{
    if (m_test_cases)
    {
        delete []m_test_cases;
        m_test_cases = NULL;
    }
    //cout.close();
}

int HttpServer::sendsegment(int s, string buffer)
{
    int result = send(s,buffer.c_str(), buffer.length(), 0);
    if(result < 0) return 0;
    else return 1;
}

// generate response code. send response
void HttpServer::sendresponse(int s, int code, struct HttpRequest *prequest, string content)
{
    string buffer;
    char *len = new char[32];
    sprintf(len,"%d",content.length());
    string len_str(len);
    delete []len;
    prequest->responsecode = code;
    // generate response head
    switch(code)
    {        
        case 200:{
            buffer = "HTTP/1.1 200 OK\r\nServer: Server/1.0\r\nContent-Type: "
            +prequest->prefix
            +"\r\nAccept-Ranges: bytes\r\nContent-Length: "
            +len_str+
            "\r\nConnection: close\r\nAccess-Control-Allow-Origin: *\r\n\r\n"
            +content;
            break;
        }
        default:
                break;
    }

	#ifdef DEBUG
    	cout << "=======sendresponse content is " << content << endl;
    	cout << "=======sendresponse content len is " << content.length() << endl;
		cout << "=======buffer is " << buffer << endl;
	#endif
    sendsegment(s, buffer);
}

int HttpServer::getrequest(string requestbuf,struct HttpRequest *prequest)
{
    int method_index = requestbuf.find(" ",0);
    int path_index = requestbuf.find(" ",method_index+1);
    if (method_index > -1)
    {
        prequest->method = requestbuf.substr(0,method_index);
        if (path_index > -1)
        {
           prequest->path = requestbuf.substr(method_index+1,path_index-method_index-1);
        }
    }    
	#ifdef DEBUG
    	cout << "prequest->method: " << prequest->method << endl << "prequest->path: " << prequest->path << endl;
	#endif
    

    if(prequest->path.find('?') == string::npos)
    {
        //get the com module send data
        int content_index = requestbuf.find("\r\n\r\n",0);
		#ifdef DEBUG
        	cout<<"requestbuf is: " << requestbuf << endl;
        	cout << "content_index is " << content_index << endl;
		#endif
        if (content_index > -1)
        {
            prequest->content = requestbuf.substr(content_index+strlen("\r\n\r\n"));
			#ifdef DEBUG
            	cout << "prequest->content is:" << prequest->content << endl;
            	cout << "prequest->content length " << prequest->content.length() << endl;            
			#endif
        }
    }
    else 
    {
        int session_index = prequest->path.find("?");
        prequest->content = prequest->path.substr(session_index+1);
        #ifdef DEBUG
            cout << "prequest->content is " << prequest->content << endl;
        #endif
    }
    if(prequest->method == "GET")
    {
        return GET;
    }
    else if(prequest->method == "POST")
    {
        return POST;
    }
    return -1;
}

void HttpServer::parse_json_str(string case_node)
{
    Json::Reader reader;
    Json::Value value;

    bool parsed = reader.parse(case_node, value);
    if (!parsed) // try to parse as a file
    {// "test.json" is for verify
        cout << case_node << endl;
        std::ifstream test(case_node.c_str(), std::ifstream::binary);
        parsed = reader.parse( test, value, false );
    }

    if (parsed)
    {
        m_totalBlocks = atoi(value["totalBlk"].asString().c_str());
        m_current_block_index = atoi(value["currentBlk"].asString().c_str());
        m_totalcaseCount = atoi(value["casecount"].asString().c_str());
        m_exeType = value["exetype"].asString();


        const Json::Value arrayObj = value["cases"];
        m_block_case_count = arrayObj.size();

        if (m_test_cases)
        {
            delete []m_test_cases;// core dump with this?
            m_test_cases = NULL;
        }
        m_test_cases = new TestCase[m_block_case_count];

        for (int i = 0; i < m_block_case_count; i++)
        {
            m_test_cases[i].init(arrayObj[i]);
        }
    }
}

void HttpServer::cancel_time_check()
{
    timer.it_value.tv_sec = 0 ;
    timer.it_value.tv_usec = 0;
    timer.it_interval.tv_sec = 0;
    timer.it_interval.tv_usec = 0;
    setitimer ( ITIMER_REAL, &timer, NULL ); // set timer with value 0 will stop the timer
    // refer to http://linux.die.net/man/2/setitimer, each process only have 1 timer of the same type.
}

void HttpServer::set_timer()
{
    timer.it_value.tv_sec = 30;
    timer.it_value.tv_usec = 0;
    timer.it_interval.tv_sec = 60;
    timer.it_interval.tv_usec = 0;
    int ret = setitimer ( ITIMER_REAL, &timer, NULL );
    if (ret < 0) perror("error: set timer!!!");
}

void HttpServer::processpost(int s,struct HttpRequest *prequest)
{
	#ifdef DEBUG
	    cout << "prequest->path is:" << prequest->path << endl;
	#endif
    prequest->prefix = "application/json";
    string json_str = "";
    string json_parse_str = "";
    
	if (prequest->path.find("/init_test") != string::npos)
    {
        m_block_finished = false;
        m_set_finished = false;
        m_timeout_count = 0;
        cout << "[ init the test suit ]" << endl;
        //outputFile << "[ init the test suit ]" << endl;
        parse_json_str(prequest->content);

        if (g_test_suite.empty() == false)
		{	
			killAllWidget();
            start_client3();
        }
        else
		{
			#ifdef DEBUG
            	cout << "no g_client_command" << endl;
			#endif
		}

        m_block_case_index = 0;
        if (m_current_block_index == 1)//the first block,start client
            m_total_case_index = 0;

        json_str = "{\"OK\":1}";
    }
    else if(prequest->path == "/check_server")
    {
        cout << "[ checking server, and found the server is running ]" << endl;
        //outputFile << "[ checking server, and found the server is running ]" << endl;
        json_str = "{\"OK\":1}";
    }
    else if(prequest->path == "/check_server_status")
    {
        Json::Value status;
        status["block_finished"] = m_block_finished ? 1 : 0;
        status["finished"] = m_set_finished ? 1 : 0;
        status["launch_fail"] = m_failto_launch;
        json_str = status.toStyledString();
		#ifdef DEBUG
        	cout << "m_totalBlocks=" <<m_totalBlocks << " m_current_block_index=" << m_current_block_index << " m_block_case_count=" << m_block_case_count << " m_totalcaseCount=" << m_totalcaseCount << " m_total_case_index=" << m_total_case_index << " m_block_case_index=" << m_block_case_index << " m_timeout_count="<<m_timeout_count<<endl;
		#endif
    }
    else if(prequest->path == "/shut_down_server")
    {
        killAllWidget(); // kill all widget when shutdown server
        json_str = "{\"OK\":1}";
        gIsRun = 0;
    }
    else if(prequest->path.find("/init_session_id",0) != string::npos)
    { 
        json_str = "{\"OK\":1}";
        int index = prequest->path.find('=',0);
        if (index != -1) {
            m_running_session = prequest->path.substr(index+1,prequest->path.length()-1-index);
            cout << "[ sessionID: " << m_running_session << " is gotten from the client ]" << endl;
            //outputFile<< "[ sessionID: " << m_running_session << "is gotten from the client ]" << endl;
        }
        else
        {
            cout << "[ invalid session id ]" << endl;
            //outputFile << "[ invalid session id ]" << endl;
        }
    }
    else if(prequest->path.find("/ask_next_step",0) != string::npos)
    {
		if (m_block_finished || m_set_finished)
        {
            m_need_restart_client = true;
            json_str = "{\"step\":\"stop\"}";
        }
        else
            json_str = "{\"step\":\"continue\"}";

        m_timeout_count = 0;// reset the timeout count
    }
    else if(prequest->path.find("/auto_test_task",0) != string::npos) // invoke by index.html
    {
        if (m_test_cases == NULL)
        {
            json_str = "{\"OK\":\"no case\"}";
			#ifdef DEBUG
            	cout << json_str << endl;
			#endif
        }
        else if (m_exeType != "auto")
        {            
            json_str = "{\"none\":0}";
			#ifdef DEBUG
            	cout << json_str << endl;
			#endif
        }
        else
        {
            string error_type = "";
            bool find_tc = get_auto_case(prequest->content,&error_type);
            if (find_tc == false)
            {
                json_str = "{\""+error_type+"\":0}";
				#ifdef DEBUG
                	cout << json_str << endl;
				#endif
            }
            else
            {
                json_str = m_test_cases[m_block_case_index].to_json().toStyledString();               		
				#ifdef DEBUG
                	cout << "send case: m_block_case_index is " << m_block_case_index << endl;
				#endif
            }
        }
    }
    else if(prequest->path.find("/manual_cases",0) != string::npos) // invoke by index.html
    {
        if (!m_test_cases)
        {
            json_str = "{\"OK\":\"no case\"}";
				#ifdef DEBUG
                	cout << json_str << endl;
				#endif
        }
        else if (m_exeType == "auto")
        {
            json_str = "{\"none\":0}";
				#ifdef DEBUG
                	cout << json_str << endl;
				#endif
        }
        else
        {
            Json::Value arrayObj;
            for (int i = 0; i < m_block_case_count; i++)
                arrayObj.append(m_test_cases[i].to_json());

            json_str = arrayObj.toStyledString();
        }
    }
    else if(prequest->path.find("/case_time_out",0) != string::npos)
    {
        if (!m_test_cases)
        {
            json_str = "{\"OK\":\"no case\"}";
				#ifdef DEBUG
                	cout << json_str << endl;
				#endif
        }
        else if (m_block_case_index < m_block_case_count)
        {
            checkResult(&m_test_cases[m_block_case_index]);
            json_str = "{\"OK\":\"timeout\"}";
        }
        else
        {
            json_str = "{\"OK\":\"case out of index\"}";
                #ifdef DEBUG
                    cout << json_str << endl;
                #endif
        }
    }
    else if(prequest->path.find("/commit_manual_result",0) != string::npos)
    {
        if ((prequest->content.length() == 0) || (!m_test_cases))
        {
            json_str = "{\"OK\":\"no case\"}";
				#ifdef DEBUG
                	cout << json_str << endl;
				#endif
        } 
        else
        {
            find_purpose(prequest, false); // will set index in find_purpose
            json_str = "{\"OK\":1}";
        }
    }
	else if(prequest->path.find("/check_execution_progress",0) != string::npos) //invoke by index.html
    {
        char *total_count = new char[16];
        sprintf(total_count,"%d",m_totalcaseCount);
        char *current_index = new char[16];
        sprintf(current_index,"%d",m_total_case_index+1);

        string count_str(total_count);
        string index_str(current_index);
        json_str = "{\"total\":"+count_str+",\"current\":"+index_str+",\"last_test_result\":\""+m_last_auto_result+"\"}";
        printf("Total: %s, Current: %s\nLast Case Result: %s" ,total_count, current_index, m_last_auto_result.c_str());

		m_last_auto_result = "BLOCK"; // should not set as BLOCK here?

        delete []total_count;
        delete []current_index;
    }
    else if ((prequest->path == "/generate_xml") || (prequest->path == "/get_test_result"))//no test
    {
        cancel_time_check();
		#ifdef DEBUG
        	cout<<"===m_block_case_index is "<<m_block_case_index<<"\nm_block_case_count is "<<m_block_case_count<<"\nm_total_case_index is "<<m_total_case_index<<"\nm_totalcaseCount is "<<m_totalcaseCount<<endl;
		#endif

        if (m_exeType == "auto")
        {
            if (m_block_case_index < m_block_case_count)
                m_block_finished = false;
            else
                m_block_finished = true;

            if (m_total_case_index < m_totalcaseCount)
                m_set_finished = false;
            else
                m_set_finished = true;
        }
        else
        {
            m_block_finished = true; 
            m_current_block_index++;
            if (m_current_block_index > m_totalBlocks) m_set_finished = true;// m_current_block_index start from 1.
        }
        
        if (!m_test_cases)
        {
            json_str = "{\"OK\":\"no case\"}";
			#ifdef DEBUG
                cout << json_str << endl;
			#endif
        } 
        else
        {
            Json::Value root;
            Json::Value arrayObj;
            for (int i = 0; i < m_block_case_count; i++)
                arrayObj.append(m_test_cases[i].result_to_json());

            char count[8];
            memset(count, 0, 8);
            sprintf(count, "%d", m_block_case_count);
            root["count"] = count;
            root["cases"] = arrayObj;

            json_str = root.toStyledString();
        }
    }
    else if (prequest->path == "/commit_result")//for auto case
    {
        if ((prequest->content.length() == 0) || (!m_test_cases))
        {
            json_str = "{\"OK\":\"no case\"}";
			#ifdef DEBUG
                cout << json_str << endl;
			#endif
            sendresponse(s, 200, prequest, json_str);
            return;
        }
       
        m_block_case_index++;
        m_total_case_index++;
   
		#ifdef DEBUG
	        cout<<"start ++index"<<endl;
		#endif
        
		#ifdef DEBUG
	        cout<<"commit_result: m_block_case_index is "<<m_block_case_index<<endl;
	        cout<<"commit_result: m_total_case_index is "<<m_total_case_index<<endl;
		#endif
        find_purpose(prequest, true);

        json_str = "{\"OK\":1}";
        if(m_need_restart_client == true)
        {
            sendresponse(s, 200, prequest, json_str);
            m_start_auto_test = 0;
           
            killAllWidget();

            printf("[ start new client in 5sec ]\n");
            sleep(5);
            m_start_auto_test = 1;
            m_need_restart_client = false;
            start_client3();
            return;
        }
    }
    else
	{
		#ifdef DEBUG
	        cout << "=================unknown request: " << prequest->path << endl;
		#endif
	}
    if (json_str != "")
        sendresponse(s, 200, prequest, json_str);
}

//split function for string
std::vector<std::string> split(std::string str,std::string pattern)
{
    std::string::size_type pos;
    std::vector<std::string> result;
    str+=pattern;//extend string so that operate easyly
    unsigned int size=str.size();

    for(unsigned int i=0; i<size; i++)
    {
     pos=str.find(pattern,i);
     if(pos<size)
     {
         std::string s=str.substr(i,pos-i);
         result.push_back(s);
         i=pos+pattern.size()-1;
     }
    }
    return result;
}

void HttpServer::find_purpose(struct HttpRequest *prequest, bool auto_test)
{
	#ifdef DEBUG
	    cout << "find_purpose =============content:" << prequest->content << endl;
	#endif
   
    string purpose = "";
    string result = "";
    string msg = "";
    string content = "";
  
    ComFun comfun;
    char* tmp = comfun.UrlDecode(prequest->content.c_str());
    content = tmp;
    delete[] tmp;// free memory from comfun
	#ifdef DEBUG
	    cout<<"urldecode:content is "<<content<<endl;
	#endif

    std::vector<std::string> splitstr=split(content,"&");
	#ifdef DEBUG
	    cout << "The result:" <<endl;
	#endif
    for(unsigned int i=0; i<splitstr.size(); i++)
    {
        vector<string> resultkey = split(splitstr[i],"=");
		#ifdef DEBUG
	        cout << splitstr[i] << endl;
            cout << resultkey[0] << endl;
		#endif
        if (resultkey[0] == "purpose")
            purpose = resultkey[1];
        else if (resultkey[0] == "result")
            result = resultkey[1];
        else if (resultkey[0] == "msg")
            msg = resultkey[1];
    }
	#ifdef DEBUG
	    cout<<"purpose:"+purpose<<endl;
	    cout<<"result:"+result<<endl;
	    cout<<"msg:"+msg<<endl;
	#endif


    bool found = false;
    for (int i = 0; i < m_block_case_count; i++)
    {
        if (m_test_cases[i].purpose == purpose)
        {
            m_test_cases[i].set_result(result, msg);
            found = true;
            if (!auto_test) // should auto test use this logic?
                m_block_case_index = i; // set index by purpose found
            break;
        }
    }
    if (!found)
        cout << "[ Error: can't find any test case by key: " << purpose << " ]" << endl;

    if (auto_test)
        m_last_auto_result = result;
}

void* processthread(void *para)
{
    string recvstr = "";
    char *buffer = new char[MAX_BUF]; // suppose 1 case need 1k, 100 cases will be sent each time, we need 100k memory?
    memset(buffer, 0, MAX_BUF);
    long iDataNum =0;
    int recvnum=0;
    HttpServer *server = (HttpServer *)para;
    //int clientsocket = *((int *)para);
    //HttpServer *obj = (HttpServer *)para;
    //int clientsocket = obj->clientsocket;    
    struct HttpRequest httprequest;
    httprequest.content = "";
    httprequest.path = "";
    httprequest.rangeflag = 0;
    httprequest.rangestart = 0;

    while(1)
    {
        #ifdef DEBUG 
            printf("clinetsocket id is %d\n", server->clientsocket);
        #endif
        iDataNum = recv(server->clientsocket,buffer+recvnum,MAX_BUF-recvnum-1,0);
        #ifdef DEBUG
            cout << "iDataNum is "<<iDataNum << endl;
        #endif      
        if(iDataNum <= 0)
        {
                delete []buffer;
                close(server->clientsocket);
                pthread_exit(NULL);
                return 0;
        }
        recvnum += iDataNum;
        
        if ((strstr(buffer,"\r\n\r\n")!=NULL || strstr(buffer,"\n\n")!=NULL) 
            && (iDataNum % 1024 != 0)) //sdb will split the data into blocks, the length of each block is 1024*n except the last block. so we can't break if the length is 1024*n
        {
            buffer[recvnum] = '\0';
			recvstr = buffer;
            #ifdef DEBUG 
                cout << "recvstr is: " << recvstr << endl;
            #endif
            break;
        }
    }
	delete []buffer;
    // parse request and process it
    switch(server->getrequest(recvstr,&httprequest))
    {
    case GET:
    case POST:
            server->processpost(server->clientsocket,&httprequest);
            break;
    default:
            break;
    }
    //insertlognode(pfilelog,&httprequest);    
    close(server->clientsocket);
    pthread_exit(NULL);
    return 0;
}

void timer_handler(int signum)
{   
    #ifdef DEBUG 
        cout<<"time out\n"<<endl;
    #endif
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
        //char ch;
        //while(read(sockfd, &ch, 1)) printf("%c", ch);
        close(sockfd);
        #ifdef DEBUG
            cout<<"finish send timeout cmd\n"<<endl;//report error: accept client socket !!!: Interrupted system call?
        #endif
    }
}

bool HttpServer::get_auto_case(string content, string *type)
{
    if(m_start_auto_test){
        if (content != "")
        {
            string value = content.substr(content.find("=")+1);
            if (value.empty() == false)
            {
		        #ifdef DEBUG
	                cout<<"value is:"+value<<endl;
		        #endif
                if (m_running_session == value)
                {
                    //do the test
                    //printf("session id ==\n");
                    if (m_block_case_index < m_block_case_count){
                        set_timer();
                        m_test_cases[m_block_case_index].set_start_at();
                        m_test_cases[m_block_case_index].print_info_string();
                        //outputFile << "[case] execute case:\nTestCase: " + m_test_cases[m_block_case_index].purpose + "\nTestEntry: " +m_test_cases[m_block_case_index].entry << endl;
                        return true;
                    }
                    else{
                        cout << endl << "[ no auto case is available any more ]" << endl;
                        //outputFile <<"[ no auto case is available any more ]" << endl;
                        *type = "none";
                        m_block_finished = true;
                        if (m_current_block_index == m_totalBlocks)
                            m_set_finished = true; // the set is finished if current block is the last block
                    }
                }
                else
                {
                   //sprint ("[ sessionID: %s in auto_test_task(), on server side, the ID is %s ]" % (parsed_query['session_id'][0], TestkitWebAPIServer.running_session_id));
                   cout << "[ Error: invalid session ID ]" << endl;
                   //outputFile<< "[ Error: invalid session ID ]" <<endl;
                   *type = "invalid";
                }
            }
        }
    }
    else
    {
        cout << "\n[ restart client process is activated, exit current client ]" << endl;
        //outputFile << "\n[ restart client process is activated, exit current client ]" << endl;

        *type = "stop";
    }
    return false;
}

void HttpServer::StartUp()
{
    //cout.open("httpserver_log.txt",ios::out|ios::app); 
    
    #ifdef DEBUG
    cout<<"httpserver.g_port is:"+g_port<<endl;
    cout<<"httpserver.g_hide_status is:"+g_hide_status<<endl;
    cout<<"httpserver.g_pid_log is:"+g_pid_log<<endl;
    cout<<"httpserver.g_test_suite is:"+g_test_suite<<endl;
    cout<<"httpserver.g_exe_sequence is:"+g_exe_sequence<<endl;
    cout<<"httpserver.g_enable_memory_collection is:"+g_enable_memory_collection<<endl; 
    #endif
    
    int serversocket;
    gServerStatus = 1;
    struct sockaddr_in server_addr;
    struct sockaddr_in clientAddr;
    int addr_len = sizeof(clientAddr);

    if((serversocket = socket(AF_INET,SOCK_STREAM,0)) < 0)
    {
        cout<<"error: create server socket!!!"<<endl;
        return;
    }

    bzero(&server_addr,sizeof(server_addr));
    server_addr.sin_family =AF_INET;
    server_addr.sin_port = htons(SERVER_PORT);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    int tmp = 1;
    setsockopt(serversocket, SOL_SOCKET, SO_REUSEADDR, &tmp, sizeof(int));
    if(bind(serversocket,(struct sockaddr *)&server_addr,sizeof(server_addr)) < 0)
    {
            cout<<"error: bind address !!!!"<<endl;
            return;
    }

    if(listen(serversocket,5)<0)
    {
            cout<<"error: listen !!!!"<<endl;
            return;
    }
    gIsRun = 1;
    printf("[Server is running.....]\n");
    //outputFile<<"[Server is running.....]\n"<<endl;
    
    while(gIsRun)
    {
        clientsocket = accept(serversocket,(struct sockaddr *)&clientAddr,(socklen_t*)&addr_len);
        if(clientsocket < 0)
        {
                cout<<"error: accept client socket !!!"<<endl;
                continue;
        }
        if(gServerStatus == 0)
        {
                close(clientsocket);
        }
        else if(gServerStatus == 1)
        {
                pthread_t threadid;
                //int temp = 
                pthread_create(&threadid, NULL, processthread, (void *)this);
                //must have,otherwise the thread can not exit
                if(threadid !=0)
                {// can't exit thread without below code?
                    pthread_join(threadid,NULL);
                }
        }        
    }
    close(serversocket);
}

void HttpServer::checkResult(TestCase* testcase)
{
    #ifdef DEBUG
    cout << testcase->is_executed << endl;
	#endif
    if (!testcase->is_executed) {
        cout << "[ Warning: time is out, test case \"" << testcase->purpose << "\" is timeout, set the result to \"BLOCK\", and restart the client ]" << endl;
        //outputFile << "[ Warning: time is out, test case \"" << testcase->purpose << "\" is timeout, set the result to \"BLOCK\", and restart the client ]" << endl;
        //try:
        //    print "[ Warning: time is out, test case \"%s\" is timeout, set the result to \"BLOCK\", and restart the client ]" % case.purpose
        //except Exception, e:
        //    print "[ Warning: time is out, test case \"%s\" is timeout, set the result to \"BLOCK\", and restart the client ]" % str2str(case.purpose)
        //    print "[ Error: found unprintable character in case purpose, error: %s ]\n" % e

        testcase->set_result("BLOCK", "Time is out");
        m_start_auto_test = 0;
        //printf("[ kill existing client, pid: %d ]\n", client_process_id);
        //kill(client_process_id, SIGKILL);

        killAllWidget();

        cout << "[ start new client in 5sec ]" << endl;
        //outputFile << "[ start new client in 5sec ]" << endl;
        sleep(5);

        m_start_auto_test = 1;
	    #ifdef DEBUG
        cout<<"========================m_block_case_index:"<<m_block_case_index<<endl;
		#endif
    }
    else {
        cout << "[ test case \"" << testcase->purpose << "\" is executed in time, and the result is testcase->result ]" << endl;
        //try:
        //    print "[ test case \"%s\" is executed in time, and the result is %s ]" % (case.purpose, case.result)
        //except Exception, e:
        //    print "[ test case \"%s\" is executed in time, and the result is %s ]" % (str2str(case.purpose), str2str(case.result))
        //    print "[ Error: found unprintable character in case purpose, error: %s ]\n" % e
    }

    m_timeout_count++;
    if (m_timeout_count >= 3) // finish current block if timeout contineously for 3 times
    {
        m_timeout_count = 0;

        m_total_case_index += m_block_case_count - m_block_case_index;
        if (m_total_case_index >= m_totalcaseCount) m_set_finished = true;

        m_block_case_index = m_block_case_count;
        m_block_finished = true;
    }
    else 
    {
        m_block_case_index++;
        m_total_case_index++;
        start_client3();// start widget again in case it dead
    }
}

void HttpServer::killAllWidget()
{
    system("echo 3 > /proc/sys/vm/drop_caches");// what for?
    //system("kill -9 ` ps -ef | grep wrt-launcher | grep -v grep |  awk '{printf $2};{printf \" \"}'`");
    system("killall wrt-launcher");

    char buf[128];
    memset(buf, 0, 128);
    char cmd[256];
    FILE *pp;
    if( (pp = popen("wrt-launcher -l | awk '{print $NF}' | sed -n '3,$p'", "r")) == NULL )
    {
        cout << "popen() error!" << endl;
        return;
    }

    while(fgets(buf, sizeof buf, pp))
    {
        cout << buf << endl;
        buf[strlen(buf)-1] = 0; // remove the character return at the end.

        memset(cmd, 0, 256);
        sprintf(cmd, "wrt-launcher -k %s \n", buf);// use wrt-launcher to kill widget
        //sprintf(cmd, "kill -9 `ps -ef | grep %s | grep -v grep | awk '{printf $2};{printf \" \"}'`\n", buf);
        cout << cmd << endl;
        system(cmd);
        memset(buf, 0, 128);
    }
    pclose(pp);
}

void HttpServer::start_client3()
{
    string cmdstring = "wrt-launcher -s `wrt-launcher -l | grep " + g_test_suite + " | awk '{print $NF}'`";
    string killcmd = "wrt-launcher -k `wrt-launcher -l | grep " + g_test_suite + " | awk '{print $NF}'`";
    while (!start_client(cmdstring)) 
    {
        m_failto_launch++;
        sleep(10);// try until start widget success
        system(killcmd.c_str());// kill again if launch fail
    }
    m_failto_launch = 0;
}

bool HttpServer::start_client(string cmdstring)
{
    bool ret = false;

    char buf[128];
    memset(buf, 0, 128);
    FILE *pp;
    cout << cmdstring << endl;
    if( (pp = popen(cmdstring.c_str(), "r")) == NULL )
    {
        cout << "popen() error!" << endl;
        return ret;
    }

    while(fgets(buf, sizeof buf, pp))
    {
        cout << buf << endl;
        if (strstr(buf, "result: launched")) ret = true;
    }
    pclose(pp);

    return ret;
}