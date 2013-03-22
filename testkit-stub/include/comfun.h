#include <stdio.h>
#include <string.h>
#include <string>
#include <vector>
using namespace std;
class ComFun {
public:
	ComFun();
	virtual ~ComFun();
public:
	static char CharToInt(char ch);
	static char StrToBin(char *str);
	static char* UrlDecode(const char *str);
	static std::vector<std::string> split(std::string str, std::string pattern);
};

