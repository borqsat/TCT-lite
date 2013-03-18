#include <stdio.h>
#include <iostream>
#include <string.h>

class ComFun
{
public:
	ComFun();
	virtual ~ComFun();
public:
	char CharToInt(char ch);
	char StrToBin(char *str);
	char* UrlDecode(const char *str);
};


