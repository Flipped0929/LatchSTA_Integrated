/**
 * @file benchmark.h
 * @brief 找到对应的函数并执行
 * @details
 * @author zli
 * @version 1.0
 * @date 2020-12-07
*/
#ifndef GUARD_function
#define GUARD_function

#include <string>
#include <vector>
using namespace std;

/**
 * @brief Test if the character c is in the string str.
 * 
 * @param c 
 * @param str 
 * @return true 
 * @return false 
 */
inline bool isCharIn(char c, string str)
{
    for (size_t i = 0; i < str.size(); ++i)
        if (c == str[i])
            return true;
    return false;
}


inline void splitString(const std::string&, const std::string&, vector<string> &words);
bool benchmarkConversion(char,char);
bool printrsltfile(char, char,char);
//void benchmark(const std::string&);


#endif