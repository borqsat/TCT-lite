#include <stdio.h>
#include "comfun.h"

ComFun::ComFun()
{

}
ComFun::~ComFun()
{

}

char ComFun::CharToInt(char ch){
	if(ch>='0' && ch<='9')return (char)(ch-'0');
	if(ch>='a' && ch<='f')return (char)(ch-'a'+10);
	if(ch>='A' && ch<='F')return (char)(ch-'A'+10);
	return -1;
}

char ComFun::StrToBin(char *str){
	char tempWord[2];
	char chn;
	tempWord[0] = CharToInt(str[0]); //make the B to 11 -- 00001011
	tempWord[1] = CharToInt(str[1]); //make the 0 to 0 -- 00000000
	chn = (tempWord[0] << 4) | tempWord[1]; //to change the BO to 10110000
	return chn;
}
char* ComFun::UrlDecode(const char *str)
{
	char tmp[2];
	int i = 0,idx = 0,ndx,len = strlen(str);
	char *output = new char[len+1];
	//output =  new char[len+1];
	memset(output,0,len+1);
	int j = 0;
	while(i<len){
		if(*(str+i) == '%'){
			tmp[0] = *(str+i+1);
			tmp[1] = *(str+i+2);
			*(output+j) = StrToBin(tmp);
			i = i+3;
			j++;
		}
		else if(*(str+i) == '+'){
			*(output+j) = ' ';
			i++;
			j++;
		}
		else{
			*(output+j) = *(str+i);
			i++;
			j++;
		}
	}
	return output;
}

/*ComFun comfun;	
const char *gb2312 = "totalBlk=1&currentBlk=0&suite=abc&set=def&cases%5B0%5D%5Border%5D=1&cases%5B1%5D%5Border%5D=2";
char *decode = comfun.UrlDecode(gb2312);
printf("decode is %s\n",decode);*/	