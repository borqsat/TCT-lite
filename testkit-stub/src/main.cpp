#include <string>
#include <json/json.h>

#include "httpserver.h"

#define SERVER_PORT 8000
#define MAX_BUF 8192

#define GET_COMMON   0
#define GET_CGI   1
#define HEAD   2
#define POST   3
#define TRACR  4
#define BAD_REQUEST -1

int gServerStatus = 0;
int gIsRun = 0;

FILE *pfilelog = NULL;

//parse the cmd line parameters
void parse(int count,char *argv[],HttpServer *httpserver)
{
	for (int i = 1; i < count; ++i)
	{
		string argvstr = argv[i];		
		int sepindex = argvstr.find(":");
		if (sepindex > -1)
		{
			string key = argvstr.substr(0,sepindex);
			string value = argvstr.substr(sepindex+1);
			
			/*cout<<"key is:"+key<<endl;
			cout<<"value is:"+value<<endl;*/
			
			if(key == "--port")
			{
				httpserver->g_port = value;
			}
			else if(key == "--hidestatus")
			{
				httpserver->g_hide_status = value;			
			}
			else if(key == "--pid_log")
			{
				httpserver->g_pid_log = value;
			}
			else if(key == "--testsuite")
			{
				httpserver->g_test_suite = value;

				// we use shell cmd to get packageid from testsuite, then form the g_client_command
				httpserver->g_client_command = "aul_test launch `wrt-launcher -l | grep "+value+" | awk '{print $NF}'`";
			}
			else if(key == "--exe_sequence")
			{
				httpserver->g_exe_sequence = value;
			}
			else if(key == "--client_command")
			{// not use now
				//httpserver->g_client_command = new char[strlen(value)+1];
				//strcpy(httpserver->g_client_command,value);
			}
			else if(key == "--enable_memory_collection")
			{
				httpserver->g_enable_memory_collection = value;
			}
		}
		
	}
}

int main( int   argc,
          char *argv[] )
{
	HttpServer httpserver;
    if (argc > 1)
	{
		parse(argc,argv,&httpserver);	
		cout<<"httpserver.g_port is:"+httpserver.g_port<<endl;
		cout<<"httpserver.g_hide_status is:"+httpserver.g_hide_status<<endl;
		cout<<"httpserver.g_pid_log is:"+httpserver.g_pid_log<<endl;
		cout<<"httpserver.g_test_suite is:"+httpserver.g_test_suite<<endl;
		cout<<"httpserver.g_exe_sequence is:"+httpserver.g_exe_sequence<<endl;
		cout<<"httpserver.g_client_command is:"+httpserver.g_client_command<<endl;
		cout<<"httpserver.g_enable_memory_collection is:"+httpserver.g_enable_memory_collection<<endl;
	}
	
    httpserver.StartUp();

    return 0;
}

