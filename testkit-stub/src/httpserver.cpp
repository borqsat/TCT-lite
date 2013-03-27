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
#if defined(DEBUG) | defined(_DEBUG)
    #ifndef DBG_ONLY
      #define DBG_ONLY(x) do { x } while (0)         
    #endif
#else
    #ifndef DBG_ONLY
      #define DBG_ONLY(x) 
    #endif
#endif

HttpServer::HttpServer() {
	m_test_cases = NULL;
	m_exeType = "auto"; // set default to auto
	m_type = "";
	m_current_block_index = 1;
	m_totalcaseCount = 0;
	m_block_case_index = 0;
	m_block_case_count = 0;
	m_last_auto_result = "N/A";
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
	m_killing_widget = false;

	memset(&sa, 0, sizeof(sa));
	sa.sa_handler = timer_handler;
	sigaction(SIGALRM, &sa, NULL);
}

HttpServer::~HttpServer() {
	if (m_test_cases) {
		delete[] m_test_cases;
		m_test_cases = NULL;
	}
}

int HttpServer::sendsegment(int s, string buffer) {
	int result = send(s, buffer.c_str(), buffer.length(), 0);
	if (result < 0)
		return 0;
	else
		return 1;
}

// generate response code. send response
void HttpServer::sendresponse(int s, int code, struct HttpRequest *prequest,
		string content) {
	string buffer;
	char *len = new char[32];
	sprintf(len, "%d", content.length());
	string len_str(len);
	delete[] len;
	prequest->responsecode = code;
	// generate response head
	switch (code) {
	case 200: {
		buffer =
				"HTTP/1.1 200 OK\r\nServer: Server/1.0\r\nContent-Type: "
						+ prequest->prefix
						+ "\r\nAccept-Ranges: bytes\r\nContent-Length: "
						+ len_str
						+ "\r\nConnection: close\r\nAccess-Control-Allow-Origin: *\r\n\r\n"
						+ content;
		break;
	}
	default:
		break;
	}

    DBG_ONLY(
	   cout << "=======sendresponse content is " << content << endl;
	   cout << "=======sendresponse content len is " << content.length() << endl;
	   cout << "=======buffer is " << buffer << endl;
    );

	sendsegment(s, buffer);
}

int HttpServer::getrequest(string requestbuf, struct HttpRequest *prequest) {
	std::vector < std::string > splitstr = ComFun::split(requestbuf, " ");
	if (splitstr.size() >= 2) {
		prequest->method = splitstr[0];
		prequest->path = splitstr[1];
	}
    DBG_ONLY(
	   cout << "prequest->method: " << prequest->method << endl << "prequest->path: " << prequest->path << endl;
    );

	if (prequest->path.find('?') == string::npos) {
		//get the com module send data
		int content_index = requestbuf.find("\r\n\r\n", 0);
        DBG_ONLY(
            cout<<"requestbuf is: " << requestbuf << endl;
            cout << "content_index is " << content_index << endl;
        );
		if (content_index > -1) {
			prequest->content = requestbuf.substr(
					content_index + strlen("\r\n\r\n"));
            DBG_ONLY(
                cout << "prequest->content is:" << prequest->content << endl;
    			cout << "prequest->content length " << prequest->content.length() << endl;
            );
		}
	} else {
		int session_index = prequest->path.find("?");
		prequest->content = prequest->path.substr(session_index + 1);
        DBG_ONLY(
    		cout << "prequest->content is " << prequest->content << endl;
        );
	}
	if (prequest->method == "GET") {
		return GET;
	} else if (prequest->method == "POST") {
		return POST;
	}
	return -1;
}

void HttpServer::parse_json_str(string case_node) {
	Json::Reader reader;
	Json::Value value;

	bool parsed = reader.parse(case_node, value);
	if (!parsed) // try to parse as a file
	{ // "test.json" is for verify
		cout << case_node << endl;
		std::ifstream test(case_node.c_str(), std::ifstream::binary);
		parsed = reader.parse(test, value, false);
	}

	if (parsed) {
		m_totalBlocks = atoi(value["totalBlk"].asString().c_str());
		m_current_block_index = atoi(value["currentBlk"].asString().c_str());
		m_totalcaseCount = atoi(value["casecount"].asString().c_str());
		m_exeType = value["exetype"].asString();

		const Json::Value arrayObj = value["cases"];
		m_block_case_count = arrayObj.size();

		if (m_test_cases) {
			delete[] m_test_cases; // core dump with this?
			m_test_cases = NULL;
		}
		m_test_cases = new TestCase[m_block_case_count];

		for (int i = 0; i < m_block_case_count; i++) {
			m_test_cases[i].init(arrayObj[i]);
		}
	}
}

void HttpServer::cancel_time_check() {
	timer.it_value.tv_sec = 0;
	timer.it_value.tv_usec = 0;
	timer.it_interval.tv_sec = 0;
	timer.it_interval.tv_usec = 0;
	setitimer(ITIMER_REAL, &timer, NULL); // set timer with value 0 will stop the timer
	// refer to http://linux.die.net/man/2/setitimer, each process only have 1 timer of the same type.
}

void HttpServer::set_timer() {
	timer.it_value.tv_sec = 90;
	timer.it_value.tv_usec = 0;
	timer.it_interval.tv_sec = 90;
	timer.it_interval.tv_usec = 0;
	int ret = setitimer(ITIMER_REAL, &timer, NULL);
	if (ret < 0)
		perror("error: set timer!!!");
}

void HttpServer::processpost(int s, struct HttpRequest *prequest) {
    DBG_ONLY(
	   cout << "prequest->path is:" << prequest->path << endl;
    );
	prequest->prefix = "application/json";
	string json_str = "";
	string json_parse_str = "";

	if (prequest->path.find("/init_test") != string::npos) {
		m_block_finished = false;
		m_set_finished = false;
		m_timeout_count = 0;
		cout << "[ init the test suit ]" << endl;
		parse_json_str(prequest->content);

		if (g_test_suite.length() > 0) {
			start_client();
		} else {
            DBG_ONLY(
                cout << "no g_client_command" << endl;
            );
		}

		m_block_case_index = 0;
		if (m_current_block_index == 1)    //the first block,start client
			m_total_case_index = 0;

		json_str = "{\"OK\":1}";
	} else if (prequest->path == "/check_server") {
		cout << "[ checking server, and found the server is running ]" << endl;
		json_str = "{\"OK\":1}";
	} else if (prequest->path == "/check_server_status") {
		Json::Value status;
		status["block_finished"] = m_block_finished ? 1 : 0;
		status["finished"] = m_set_finished ? 1 : 0;
		status["launch_fail"] = m_failto_launch;
		json_str = status.toStyledString();
        DBG_ONLY(
            cout << "m_totalBlocks=" <<m_totalBlocks << " m_current_block_index=" << m_current_block_index << " m_block_case_count=" << m_block_case_count << " m_totalcaseCount=" << m_totalcaseCount << " m_total_case_index=" << m_total_case_index << " m_block_case_index=" << m_block_case_index << " m_timeout_count="<<m_timeout_count<<endl;
        );
	} else if (prequest->path == "/shut_down_server") {
		killAllWidget(); // kill all widget when shutdown server
		json_str = "{\"OK\":1}";
		gIsRun = 0;
	} else if (prequest->path.find("/init_session_id") != string::npos) {
		json_str = "{\"OK\":1}";
		int index = prequest->path.find('=');
		if (index != -1) {
			m_running_session = prequest->path.substr(index + 1);
			cout << "[ sessionID: " << m_running_session
					<< " is gotten from the client ]" << endl;
		} else {
			cout << "[ invalid session id ]" << endl;
		}
	} else if (prequest->path.find("/ask_next_step") != string::npos) {
		if (m_block_finished || m_set_finished)
			json_str = "{\"step\":\"stop\"}";
		else
			json_str = "{\"step\":\"continue\"}";

		m_timeout_count = 0; // reset the timeout count
	} else if (prequest->path.find("/auto_test_task") != string::npos) {// get current auto case
		if (m_test_cases == NULL) {
			json_str = "{\"OK\":\"no case\"}";
		} else if (m_exeType != "auto") {
			json_str = "{\"none\":0}";
		} else {
			string error_type = "";
			bool find_tc = get_auto_case(prequest->content, &error_type);
			if (find_tc == false) {
				json_str = "{\"" + error_type + "\":0}";
			} else {
				json_str =
						m_test_cases[m_block_case_index].to_json().toStyledString();
                DBG_ONLY(
                    cout << "send case: m_block_case_index is " << m_block_case_index << endl;
                );
			}
		}
	} else if (prequest->path.find("/manual_cases") != string::npos) {// invoke by index.html
		if (!m_test_cases) {
			json_str = "{\"OK\":\"no case\"}";
		} else if (m_exeType == "auto") {
			json_str = "{\"none\":0}";
		} else {
			Json::Value arrayObj;
			for (int i = 0; i < m_block_case_count; i++)
				arrayObj.append(m_test_cases[i].to_json());

			json_str = arrayObj.toStyledString();
		}
	} else if (prequest->path.find("/case_time_out") != string::npos) {
		if (!m_test_cases) {
			json_str = "{\"OK\":\"no case\"}";
		} else if (m_block_case_index < m_block_case_count) {
			checkResult(&m_test_cases[m_block_case_index]);
			json_str = "{\"OK\":\"timeout\"}";
		} else {
			json_str = "{\"OK\":\"case out of index\"}";
		}
	} else if (prequest->path.find("/commit_manual_result") != string::npos) {
		if ((prequest->content.length() == 0) || (!m_test_cases)) {
			json_str = "{\"OK\":\"no case\"}";
		} else {
			find_purpose(prequest, false); // will set index in find_purpose
			json_str = "{\"OK\":1}";
		}
	} else if (prequest->path.find("/check_execution_progress") != string::npos) {//invoke by index.html
		char *total_count = new char[16];
		sprintf(total_count, "%d", m_totalcaseCount);
		char *current_index = new char[16];
		sprintf(current_index, "%d", m_total_case_index + 1);

		string count_str(total_count);
		string index_str(current_index);
		json_str = "{\"total\":" + count_str + ",\"current\":" + index_str
				+ ",\"last_test_result\":\"" + m_last_auto_result + "\"}";

		m_last_auto_result = "BLOCK"; // should not set as BLOCK here?

		delete[] total_count;
		delete[] current_index;
	}
	//generate_xml:from index_html, a maually block finished when click done in widget
	else if (prequest->path == "/generate_xml") {
		cancel_time_check();
        DBG_ONLY(
            cout<<"===m_block_case_index is "<<m_block_case_index<<"\nm_block_case_count is "<<m_block_case_count<<"\nm_total_case_index is "<<m_total_case_index<<"\nm_totalcaseCount is "<<m_totalcaseCount<<endl;
        );
		m_block_finished = true;
		if (m_current_block_index == m_totalBlocks)
			m_set_finished = true;

		json_str = "{\"OK\":1}";
	}
	//from com module,when m_set_finished is true
	else if (prequest->path == "/get_test_result") {
		cancel_time_check();
        DBG_ONLY(
            cout<<"===m_block_case_index is "<<m_block_case_index<<"\nm_block_case_count is "<<m_block_case_count<<"\nm_total_case_index is "<<m_total_case_index<<"\nm_totalcaseCount is "<<m_totalcaseCount<<endl;
        );
		if (!m_test_cases) {
			json_str = "{\"OK\":\"no case\"}";
		} else {
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
	} else if (prequest->path == "/commit_result") {//auto case commit result
		if ((prequest->content.length() == 0) || (!m_test_cases)) {
			json_str = "{\"OK\":\"no case\"}";
		} else {
            m_block_case_index++;
            m_total_case_index++;

            DBG_ONLY(
                cout<<"start ++index"<<endl;
                cout<<"commit_result: m_block_case_index is "<<m_block_case_index<<endl;
                cout<<"commit_result: m_total_case_index is "<<m_total_case_index<<endl;
            );
            find_purpose(prequest, true);

            json_str = "{\"OK\":1}";
        }
    } else if (prequest->path == "/set_capability") {// by com-module
        Json::Reader reader;

        reader.parse(prequest->content, m_capability);

        json_str = "{\"OK\":1}";
    } else if (prequest->path.find("/capability") != string::npos) {// by test suite. only one query parameter each time
        char* tmp = ComFun::UrlDecode(prequest->content.c_str());
        string content = tmp;
        delete[] tmp; // free memory from comfun

        json_str = "{\"support\":0}";
        string name = "", value = "";
        std::vector < std::string > splitstr = ComFun::split(content, "&");
        for (unsigned int i = 0; i < splitstr.size(); i++) {
            vector < string > resultkey = ComFun::split(splitstr[i], "=");
            if (resultkey[0] == "name") name = resultkey[1];
            if (resultkey[0] == "value") value = resultkey[1];
        }

        if (m_capability[name].isBool()) {// for bool value, omit the value part
            json_str = "{\"support\":1}";
        }
        else if (m_capability[name].isInt()) {
            if (m_capability[name].asInt() == atoi(value.c_str()))
                json_str = "{\"support\":1}";
        }
        else if (m_capability[name].isString()) {
            if (m_capability[name].asString() == value)
                json_str = "{\"support\":1}";
        }
        cout << json_str << endl;
	} else {
        cout << "=================unknown request: " << prequest->path << endl;
	}
    
    DBG_ONLY(cout << json_str << endl;);

	if (json_str != "")
		sendresponse(s, 200, prequest, json_str);
}

void HttpServer::find_purpose(struct HttpRequest *prequest, bool auto_test) {
    DBG_ONLY(
	   cout << "find_purpose =============content:" << prequest->content << endl;
    );

	string purpose = "";
	string result = "";
	string msg = "";
	string content = "";

	char* tmp = ComFun::UrlDecode(prequest->content.c_str());
	content = tmp;
	delete[] tmp; // free memory from comfun
    DBG_ONLY(
	   cout<<"urldecode:content is "<<content<<endl;
    );

	std::vector < std::string > splitstr = ComFun::split(content, "&");
    DBG_ONLY(
	   cout << "The result:" <<endl;
    );
	for (unsigned int i = 0; i < splitstr.size(); i++) {
		vector < string > resultkey = ComFun::split(splitstr[i], "=");
        DBG_ONLY(
            cout << splitstr[i] << endl;
            cout << resultkey[0] << endl;
        );
		if (resultkey[0] == "purpose")
			purpose = resultkey[1];
		else if (resultkey[0] == "result")
			result = resultkey[1];
		else if (resultkey[0] == "msg")
			msg = resultkey[1];
	}
    DBG_ONLY(
	   cout<<"purpose:"+purpose<<endl;
	   cout<<"result:"+result<<endl;
	   cout<<"msg:"+msg<<endl;
    );

	bool found = false;
	for (int i = 0; i < m_block_case_count; i++) {
		if (m_test_cases[i].purpose == purpose) {
			m_test_cases[i].set_result(result, msg);
			found = true;
			if (!auto_test) // should auto test use this logic?
				m_block_case_index = i; // set index by purpose found
			break;
		}
	}
	if (!found)
		cout << "[ Error: can't find any test case by key: " << purpose << " ]"
				<< endl;

	if (auto_test)
		m_last_auto_result = result;
}

void* processthread(void *para) {
	string recvstr = "";
	char *buffer = new char[MAX_BUF]; // suppose 1 case need 1k, 100 cases will be sent each time, we need 100k memory?
	memset(buffer, 0, MAX_BUF);
	long iDataNum = 0;
	int recvnum = 0;
	HttpServer *server = (HttpServer *) para;
	struct HttpRequest httprequest;
	httprequest.content = "";
	httprequest.path = "";
	httprequest.rangeflag = 0;
	httprequest.rangestart = 0;

	while (1) {
        DBG_ONLY(
            printf("clinetsocket id is %d\n", server->clientsocket);
        );
		iDataNum = recv(server->clientsocket, buffer + recvnum,
				MAX_BUF - recvnum - 1, 0);
        DBG_ONLY(
            cout << "iDataNum is "<<iDataNum << endl;
        );
		if (iDataNum <= 0) {
			delete[] buffer;
			close(server->clientsocket);
			pthread_exit (NULL);
			return 0;
		}
		recvnum += iDataNum;

		if ((strstr(buffer, "\r\n\r\n") != NULL
				|| strstr(buffer, "\n\n") != NULL) && (iDataNum % 1024 != 0)) //sdb will split the data into blocks, the length of each block is 1024*n except the last block. so we can't break if the length is 1024*n
				{
			buffer[recvnum] = '\0';
			recvstr = buffer;
            DBG_ONLY(cout << "recvstr is: " << recvstr << endl;);
			break;
		}
	}
	delete[] buffer;
	// parse request and process it
	switch (server->getrequest(recvstr, &httprequest)) {
	case GET:
	case POST:
		server->processpost(server->clientsocket, &httprequest);
		break;
	default:
		break;
	}
	close(server->clientsocket);
	pthread_exit (NULL);
	return 0;
}

void timer_handler(int signum) {
    DBG_ONLY(
	   cout<<"time out\n"<<endl;
    );
	// when timeout, we send a http request to server, so server can check result. no other convinent way to do it?
	const char *strings =
			"GET /case_time_out HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: Close\r\n\r\n";
	int sockfd = socket(AF_INET, SOCK_STREAM, 0);
	struct sockaddr_in address;
	address.sin_family = AF_INET;
	address.sin_addr.s_addr = inet_addr("127.0.0.1");
	address.sin_port = htons(SERVER_PORT);
	int len = sizeof(address);
	int result = connect(sockfd, (struct sockaddr *) &address, len);
	if (result == -1) {
		printf("fail to send timeout request to server!\n");
	} else {
		write(sockfd, strings, strlen(strings));
		close(sockfd);
        DBG_ONLY(
            cout<<"finish send timeout cmd\n"<<endl; //report error: accept client socket !!!: Interrupted system call?
        );
	}
}

bool HttpServer::get_auto_case(string content, string *type) {
	if (!m_killing_widget) {
		if (content != "") {
			string value = content.substr(content.find("=") + 1);
			if (value.length() > 0) {
                DBG_ONLY(
                    cout<<"value is:"+value<<endl;
                );
				if (m_running_session == value) {
					if (m_block_case_index < m_block_case_count) {
						set_timer();
						m_test_cases[m_block_case_index].set_start_at();
						m_test_cases[m_block_case_index].print_info_string();
						return true;
					} else {
						cout << endl << "[ no auto case is available any more ]" << endl;
						*type = "none";
						m_block_finished = true;
						if (m_current_block_index == m_totalBlocks)
							m_set_finished = true; // the set is finished if current block is the last block
					}
				} else {
					cout << "[ Error: invalid session ID ]" << endl;
					*type = "invalid";
				}
			}
		}
	} else {
		cout << "\n[ restart client process is activated, exit current client ]" << endl;
		*type = "stop";
	}
	return false;
}

//start the socket server,listen to client
void HttpServer::StartUp() {
    DBG_ONLY(
	cout<<"httpserver.g_port is:"+g_port<<endl;
	cout<<"httpserver.g_hide_status is:"+g_hide_status<<endl;
	cout<<"httpserver.g_pid_log is:"+g_pid_log<<endl;
	cout<<"httpserver.g_test_suite is:"+g_test_suite<<endl;
	cout<<"httpserver.g_exe_sequence is:"+g_exe_sequence<<endl;
	cout<<"httpserver.g_enable_memory_collection is:"+g_enable_memory_collection<<endl;
    );

	int serversocket;
	gServerStatus = 1;
	struct sockaddr_in server_addr;
	struct sockaddr_in clientAddr;
	int addr_len = sizeof(clientAddr);

	if ((serversocket = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
		cout << "error: create server socket!!!" << endl;
		return;
	}

	bzero(&server_addr, sizeof(server_addr));
	server_addr.sin_family = AF_INET;
	server_addr.sin_port = htons(SERVER_PORT);
	server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

	int tmp = 1;
	setsockopt(serversocket, SOL_SOCKET, SO_REUSEADDR, &tmp, sizeof(int));
	if (bind(serversocket, (struct sockaddr *) &server_addr,
			sizeof(server_addr)) < 0) {
		cout << "error: bind address !!!!" << endl;
		return;
	}

	if (listen(serversocket, 5) < 0) {
		cout << "error: listen !!!!" << endl;
		return;
	}
	gIsRun = 1;
	cout << "[Server is running.....]" << endl;
    
    killAllWidget();

	while (gIsRun) {
		clientsocket = accept(serversocket, (struct sockaddr *) &clientAddr,
				(socklen_t*) &addr_len);
		if (clientsocket < 0) {
			cout << "error: accept client socket !!!" << endl;
			continue;
		}
		if (gServerStatus == 0) {
			close(clientsocket);
		} else if (gServerStatus == 1) {
			pthread_t threadid;
			//int temp = 
			pthread_create(&threadid, NULL, processthread, (void *) this);
			//must have,otherwise the thread can not exit
			if (threadid != 0) { // can't exit thread without below code?
				pthread_join(threadid, NULL);
			}
		}
	}
	close(serversocket);
}

void HttpServer::checkResult(TestCase* testcase) {
    DBG_ONLY(
	cout << testcase->is_executed << endl;
    );
	if (!testcase->is_executed) {
		cout << "[ Warning: time is out, test case \"" << testcase->purpose
				<< "\" is timeout, set the result to \"BLOCK\", and restart the client ]"
				<< endl;

		testcase->set_result("BLOCK", "Time is out");

        run_cmd(g_kill_cmd, "result: killed", true);

		cout << "[ start new client in 5sec ]" << endl;
		sleep(5);

        DBG_ONLY(
		cout<<"========================m_block_case_index:"<<m_block_case_index<<endl;
        );
	} else {
		cout << "[ test case \"" << testcase->purpose
				<< "\" is executed in time, and the result is testcase->result ]"
				<< endl;
	}

	m_timeout_count++;
	if (m_timeout_count >= 3) // finish current block if timeout contineously for 3 times
			{
		m_timeout_count = 0;
		if (m_current_block_index == m_totalBlocks) {
			m_set_finished = true;
			m_block_finished = true;
		} else {
			m_total_case_index += m_block_case_count - m_block_case_index;
			m_block_finished = true;
		}
	} else {
		m_block_case_index++;
		m_total_case_index++;
		start_client(); // start widget again in case it dead
	}
}

void HttpServer::killAllWidget() {
	m_killing_widget = true;

	system("echo 3 > /proc/sys/vm/drop_caches"); // what for?
	system("killall wrt-launcher");

	char buf[128];
	memset(buf, 0, 128);
	FILE *pp;
	if ((pp = popen("wrt-launcher -l | awk '{print $NF}' | sed -n '3,$p'", "r"))
			== NULL) {
		cout << "popen() error!" << endl;
		return;
	}

	int count = 1;
	while (fgets(buf, sizeof buf, pp)) {
		buf[strlen(buf) - 1] = 0; // remove the character return at the end.

		string cmd = "wrt-launcher -k "; // use wrt-launcher to kill widget
		cmd += buf;
		run_cmd(cmd, "result: killed", false);
		cout << count << endl;
		count++;
		memset(buf, 0, 128);
	}
	pclose(pp);

	m_killing_widget = false;
}

void HttpServer::start_client() {
    if (m_invalid_suite) {
        m_failto_launch++;
        return;
    }

	while (!run_cmd(g_launch_cmd, "result: launched", true)) {
        run_cmd(g_kill_cmd, "result: killed", true);
		m_failto_launch++;
		cout << m_failto_launch << endl;
		sleep(10); // try until start widget success
	}
	m_failto_launch = 0;
}

// run shell cmd. return true if the output equal to expectString. show cmd and output if showcmdAnyway.
bool HttpServer::run_cmd(string cmdString, string expectString,
		bool showcmdAnyway) {
	bool ret = false;

	char buf[128];
	memset(buf, 0, 128);
	FILE *pp;

	if ((pp = popen(cmdString.c_str(), "r")) == NULL) {
		cout << "popen() error!" << endl;
		return ret;
	}

	while (fgets(buf, sizeof buf, pp)) {
        m_output = buf;
		if (strstr(buf, expectString.c_str()))
			ret = true;
		if (ret || showcmdAnyway) { // show cmd and result if ret or showcmdAnyWay
			cout << cmdString << endl;
			cout << buf << endl;
		}
	}
	pclose(pp);

	return ret;
}