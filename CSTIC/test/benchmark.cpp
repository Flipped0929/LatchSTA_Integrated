#include <fstream>
#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <cstdlib>
#include <unistd.h>
#include <fcntl.h>
//#include "benchmark.hpp"

using namespace std;


/**
 * @brief Split a text line into seperate words, and store them in a vector of string.
 * 
 * @param str 
 * @param seps 
 * @param words 
 */
inline void splitString(const string &str, const string &seps, vector<string> &words)
{
    words.clear();
    size_t i = 0;
    while (isCharIn(str[i], seps))
        ++i;
    size_t beginIndex;
    bool isSepBefore = false;
    for (beginIndex = i; i != str.size(); ++i)
    {
        if (isCharIn(str[i], seps))
        {
            if (!isSepBefore)
            {
                words.push_back(str.substr(beginIndex, i - beginIndex));
                beginIndex = i + 1;
                isSepBefore = true;
            }
            else
                beginIndex = i + 1;
        }
        else
            isSepBefore = false;
    }
    if (!str.empty() && !isSepBefore)
        words.push_back(str.substr(beginIndex, i - beginIndex));
}

/*
char vfile[100], sdffile[100], rsltfile[100];
    sprintf(vfile, "%s.v", argv[1]);
    sprintf(sdffile, "%s.sdf", argv[1]);
    sprintf(rsltfile, "%s.rslt", argv[1]);
*/
bool benchmarkConversion(const char* rptfile,const char* tempfile)
{
    ifstream inrpt(rptfile);
    if (!inrpt)
    {
        cout << "Error in reading file " << rptfile << endl;
        return false;
    }
    ofstream temp(tempfile);
    string textLine;
    vector<string> words;
    string record;
    int cunt=0;
    while (inrpt)
    {
        getline(inrpt, textLine);
        words.clear();
        splitString(textLine, " \t", words);
        if (textLine == "#End of timing report")
        {
            temp << "End";
            temp << endl;
        }
        if ((words.size() == 0) || (words[0] == "#")|| (words[0] == "-") || ((words[0] != "Startpoint:") && (words[0] != "Endpoint") && (words[1] != "arrival")))
            continue;
        if (words[0] == "Startpoint:")
        {
            temp << words[1] << "\t" ;
            continue;
        }
        if (words[0] == "Endpoint")
        {
            temp << words[2] << "\t" ;
            continue;
        }
        if (words[1] == "arrival")
        {
            if(cunt%3 == 0)
            //if ((record != words[3]) && (("-" + record) != words[3]) && (record != ("-" + words[3])) )
            {
                temp << words[3] << "\n" ;
            }
            cunt ++;
            continue;
        }
    }
    inrpt.close();
    temp.close();
    return true;
}

bool printrsltfile(const char* setupfile,const char* holdfile,const char* rsltfile)
{
    ifstream insetup(setupfile);
    if (!insetup)
    {
        cout << "Error in reading file " << setupfile << endl;
        return false;
    }
    ifstream inhold(holdfile);
    if (!inhold)
    {
        cout << "Error in reading file " << holdfile << endl;
        return false;
    }
    ofstream inrslt(rsltfile);
    inrslt << "Network " << rsltfile << "\n" 
    << "latch latch max_delay min_delay" << "\n"
    << "INPUT latch max_delay min_delay" << "\n"
    << "latch OUTPUT max_delay min_delay" << "\n";
    string setupLine,holdLine;
    vector<string> setupwords,holdwords;
    vector<vector<string> > setup,hold;
    while (insetup)
    {
        int i = 0;
        getline(insetup, setupLine);
        setupwords.clear();
        splitString(setupLine, " \t", setupwords);
        setup.push_back(setupwords);
    }
    while (inhold)
    {
        getline(inhold, holdLine);
        holdwords.clear();
        splitString(holdLine, " \t", holdwords);
        hold.push_back(holdwords);
    }
    insetup.close();
    inhold.close();
    int arr[255] = {0};
    bool flag;
    //vector<vector<string> >::iterator iterS,iterH;
    int i,j;
    for(i=0; i < setup.size()-2; i++)
    {
        int mark=0;
        for(j=0; j < hold.size()-2; j++)
        {   
            //inrslt << j << "\t"<< i <<"\n";
            if ((setup[i][0] == hold[j][0]) && (setup[i][1] == hold[j][1]))
            {
                inrslt << hold[j][0] << "\t" << hold[j][1] << "\t" << setup[j][2] << "\t" << hold[j][2] << "\n";
                arr[j] = 1;
                mark++;
                flag = 1;
            }    
        }
        if(!flag)
        {
            inrslt << setup[i][0] << "\t" << setup[i][1] << "\t" << setup[i][2] << "\t" << setup[i][2] << "\n";
        }
    }
    int mark=0;
    for(i=0; i < hold.size()-2; i++)
    {
        if(!arr[mark])
            inrslt << hold[i][0] << "\t" << hold[i][1] << "\t" << hold[i][2] << "\t" << hold[i][2] << "\n";
        mark++;
    }
    inrslt << endl;
    inrslt.close();
    return true;

}
/*
     while (inhold)
    {
        getline(inhold, holdLine);
        holdwords.clear();
        splitString(holdLine, " \t", holdwords);
        if(!arr[i])
        {
            //inrslt << holdwords[0] << "\t" << holdwords[1] << "\t" << holdwords[2] << "\t" << holdwords[2] << "\n";
            continue;
        }
        else
            continue;

*/
/*
int main(int argc, char* argv[])
{

    if(argc != 2) {
        cout << "Wrong Para!" << endl;
        cout << "Usage : ./sta NetlistName(without .v)" << endl;
	return EXIT_SUCCESS;
    }

    string folderPath = "E:\\Test\\Dir";
	if (0 != access(folderPath.c_str(), 0))
	{
		int iRst = mkdir(folderPath.c_str());   // 需要迭代创建，即创建子文件夹时父文件夹必须存在
	}

    char vfile[100], sdffile[100], rsltfile[100];
    sprintf(vfile, "%s.v", argv[1]);
    sprintf(sdffile, "%s.sdf", argv[1]);
    sprintf(rsltfile, "%s.rslt", argv[1]);
    benchmarkConversion("report_timing.hold.rpt","test.out");
    return 0;

}
*/
/*
int main()
{
/*
    string folderPath = "C:/Users/zjd/Desktop/test";
	if (0 != access(folderPath.c_str(), 0))
	{
		int iRst = mkdir(folderPath.c_str());   // 需要迭代创建，即创建子文件夹时父文件夹必须存在
	}
    string cmd = "cd " + folderPath;  
    system(cmd.c_str());

    benchmarkConversion("report_timing.hold.rpt","hold.out");
    benchmarkConversion("report_timing.setup.rpt","setup.out");
    printrsltfile("setup.out","hold.out","rslt.out");
    return 0;
}*/
