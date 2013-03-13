#include <iostream>
#include <sys/socket.h>
#include <errno.h>
#include <stdio.h>
#include <netinet/in.h>
#include <errno.h>
#include <netdb.h>
#include <sys/types.h>
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
		char *value = argv[i];		
		char *key = strsep(&value,":");
		/*printf("value is %s\n",value);
		printf("key is %s\n",key);*/
		
		if(strcmp(key, "--port")==0)
		{
			httpserver->g_port = new char[strlen(value)+1];
			strcpy(httpserver->g_port,value);
		}
		else if(strcmp(key, "--hidestatus")==0)
		{
			httpserver->g_hide_status = new char[strlen(value)+1];
			strcpy(httpserver->g_hide_status,value);			
		}
		else if(strcmp(key, "--pid_log")==0)
		{
			httpserver->g_pid_log = new char[strlen(value)+1];
			strcpy(httpserver->g_pid_log,value);
		}
		else if(strcmp(key, "--testsuite")==0)
		{
			httpserver->g_test_suite = new char[strlen(value)+1];
			strcpy(httpserver->g_test_suite,value);

			// we use shell cmd to get packageid from testsuite, then form the g_client_command
			httpserver->g_client_command = new char[strlen(value)+128];
			sprintf(httpserver->g_client_command, "aul_test launch `wrt-launcher -l | grep %s | awk '{print $NF}'`", value);
		}
		else if(strcmp(key, "--exe_sequence")==0)
		{
			httpserver->g_exe_sequence = new char[strlen(value)+1];
			strcpy(httpserver->g_exe_sequence,value);
		}
		else if(strcmp(key, "--client_command")==0)
		{// not use now
			//httpserver->g_client_command = new char[strlen(value)+1];
			//strcpy(httpserver->g_client_command,value);
		}
		else if(strcmp(key, "--enable_memory_collection")==0)
		{
			httpserver->g_enable_memory_collection = new char[strlen(value)+1];
			strcpy(httpserver->g_enable_memory_collection,value);
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
		/*printf("%s\n",httpserver.g_port);
		printf("%s\n",httpserver.g_hide_status);
		printf("%s\n",httpserver.g_pid_log);
		printf("%s\n",httpserver.g_test_suite);
		printf("%s\n",httpserver.g_exe_sequence);
		printf("%s\n",httpserver.g_client_command);
		printf("%s\n",httpserver.g_enable_memory_collection);*/
	}   	
	
    httpserver.StartUp();

    return 0;
}

