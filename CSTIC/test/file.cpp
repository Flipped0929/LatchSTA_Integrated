/**
 * @file file.cpp
 * @brief 生成文件夹并在文件夹中生成对应.out文件
 * @details
 * @author kxz
 * @version 1.0
 * @date 2021-8-16
*/

#include "file.h"
#include <cstdlib>
#include <fstream>

using std::string;
using std::ofstream;

void file(const string& s)
{
    string command = "mkdir " + s;
    system(command.c_str());
    string sp = s + "/" + s + ".blif.out";
    ofstream outfile(sp.c_str());
}