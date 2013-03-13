#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <sys/time.h>
#include <unistd.h>
#include <sys/wait.h>
#include <errno.h>
#include <sys/types.h>

void setString(char** str, char* value)
{
	if (!value) return;

	if (*str) delete[] *str;
	*str = new char[strlen(value) + 1];
	strcpy(*str, value);
}

pid_t pid;

int times = 0;
int timeout = 90; // default 90 seconds
int delta = 10000;// 0.01 seconds
struct itimerval timer ;
void timer_handler(int signum)
{
	times += delta;
	if (times > timeout * 1000000)
	{
        timer.it_value.tv_sec = 0 ;
        timer.it_value.tv_usec = 0;
        timer.it_interval.tv_sec = 0;
        timer.it_interval.tv_usec = 0;
        setitimer ( ITIMER_REAL, &timer, NULL ); // set timer with value 0 will stop the timer

        if (pid > 0) kill(pid, SIGTERM);

        exit(-1);
	}
}

int main( int   argc,
          char *argv[] )
{
	//set default value
	char* cmd = NULL;
	char* pid_log = NULL;
	bool boutput = false;

    struct sigaction sa;

	//get the parameters from cmd line
	if (argc > 1)
	{
		cmd = new char[256];
		memset(cmd, 0, 256);
		sprintf(cmd, "%s > ~/.shellexec_buffile_stdout 2> ~/.shellexec_buffile_stderr", argv[1]);
	}
	else 
	{
		printf("no cmd\n");
		return 0;
	}
	
	if (argc > 2) setString(&pid_log, argv[2]);
	else setString(&pid_log, "no_log");
	
	if (argc > 3) timeout = atoi(argv[3]);
	
	if (argc > 4)
	{
		if (strcmp(argv[4], "False") == 0) boutput = false;
		else boutput = true;
	}
	
    if (timeout > 0) {
        memset ( &sa, 0, sizeof ( sa ) ) ;

        sa.sa_handler = timer_handler;
        sigaction ( SIGALRM, &sa, NULL );

        timer.it_value.tv_sec = 0;
        timer.it_value.tv_usec = delta;
        timer.it_interval.tv_sec = 0;
        timer.it_interval.tv_usec = delta;

        setitimer ( ITIMER_REAL, &timer, NULL ) ;
    }

    //printf("%s\n", cmd);
    int status;
    if((pid = fork())<0){
        status = -1;
    }
    else if(pid = 0){
        execl("/bin/sh", "sh", "-c", cmd, (char *)0);
    }
    else{
        waitpid(pid, &status, 0);
    }    

	// free memory
	if (cmd) delete[] cmd;
	if (pid_log) delete[] pid_log;

    return 0;
}
