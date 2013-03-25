#include <stdio.h>
#include "comfun.h"

ComFun::ComFun() {

}
ComFun::~ComFun() {

}

char ComFun::CharToInt(char ch) {
	if (ch >= '0' && ch <= '9')
		return (char) (ch - '0');
	if (ch >= 'a' && ch <= 'f')
		return (char) (ch - 'a' + 10);
	if (ch >= 'A' && ch <= 'F')
		return (char) (ch - 'A' + 10);
	return -1;
}

char ComFun::StrToBin(char *str) {
	char tempWord[2];
	char chn;
	tempWord[0] = CharToInt(str[0]); //make the B to 11 -- 00001011
	tempWord[1] = CharToInt(str[1]); //make the 0 to 0 -- 00000000
	chn = (tempWord[0] << 4) | tempWord[1]; //to change the BO to 10110000
	return chn;
}
//url decode
char* ComFun::UrlDecode(const char *str) {
	char tmp[2];
	int i = 0, len = strlen(str);
	char *output = new char[len + 1];
	memset(output, 0, len + 1);
	int j = 0;
	while (i < len) {
		if (*(str + i) == '%') {
			tmp[0] = *(str + i + 1);
			tmp[1] = *(str + i + 2);
			*(output + j) = StrToBin(tmp);
			i = i + 3;
			j++;
		} else if (*(str + i) == '+') {
			*(output + j) = ' ';
			i++;
			j++;
		} else {
			*(output + j) = *(str + i);
			i++;
			j++;
		}
	}
	return output;
}

//split function for string
std::vector<std::string> ComFun::split(std::string str, std::string pattern) {
	std::string::size_type pos;
	std::vector < std::string > result;
	str += pattern; //extend string so that operate easyly
	unsigned int size = str.size();

	for (unsigned int i = 0; i < size; i++) {
		pos = str.find(pattern, i);
		if (pos < size) {
			std::string s = str.substr(i, pos - i);
			result.push_back(s);
			i = pos + pattern.size() - 1;
		}
	}
	return result;
}