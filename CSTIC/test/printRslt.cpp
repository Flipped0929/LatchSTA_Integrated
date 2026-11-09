#include <iostream>
#include <fstream>
#include <cstdlib>
#include <cstring>
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


bool printrsltfile(const char* setupfile,const char* holdfile,const char* rsltfile)//char* rsltfile)
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
	    string hold_name_0 = hold[j][0].substr(0,hold[j][0].find_last_of("."));
            string hold_name_1 = hold[j][1].substr(0,hold[j][1].find_last_of("."));
	    string setup_name_0 = setup[i][0].substr(0,setup[i][0].find_last_of("."));
            string setup_name_1 = setup[i][1].substr(0,setup[i][1].find_last_of("."));
            if ((setup_name_0 == hold_name_0) && (setup_name_1 == hold_name_1))
            {
                
                //string setup_name_0 = setup[j][2].substr(0,setup[j][2].size()-5);
                //string setup_name_1 = setup[j][1].substr(0,setup[j][1].size()-5);
                //string hold_name_0 = hold[j][0].substr(0,hold[j][0].find_last_of("."));
                //string hold_name_1 = hold[j][1].substr(0,hold[j][1].find_last_of("."));
                if(hold[j][0].find("outpad") != string::npos)
                    hold_name_0 = "OUTPUT";
                if(hold[j][1].find("outpad") != string::npos)
                    hold_name_1 = "OUTPUT";
                if(hold[j][0].find("inpad") != string::npos)
                    hold_name_0 = "INPUT";
                if(hold[j][1].find("inpad") != string::npos)
                    hold_name_1 = "INPUT";
                inrslt << hold_name_0 << "\t" << hold_name_1 << "\t" << setup[j][2] << "\t" << hold[j][2] << "\n";
                arr[j] = 1;
                mark++;
                flag = 1;
            }    
        }
        if(!flag)
        {
            string setup_name_0 = setup[i][0].substr(0,setup[i][0].find_last_of("."));
            string setup_name_1 = setup[i][1].substr(0,setup[i][1].find_last_of("."));
            //string hold_name_0 = hold[j][0].substr(0,hold[j][0].size()-5);
            //string hold_name_1 = hold[j][1].substr(0,hold[i][1].size()-5);
            if(setup[i][0].find("outpad") != string::npos)
                    setup_name_0 = "OUTPUT";
            if(setup[i][1].find("outpad") != string::npos)
                    setup_name_1 = "OUTPUT";
            if(setup[i][0].find("inpad") != string::npos)
                   setup_name_0 = "INPUT";
            if(setup[i][1].find("inpad") != string::npos)
                    setup_name_1 = "INPUT";
            inrslt << setup_name_0 << "\t" << setup_name_1 << "\t" << setup[i][2] << "\t" << setup[i][2] << "\n";
        }
    }
    int mark=0;
    for(i=0; i < hold.size()-2; i++)
    {
        if(!arr[mark])
        {
            string hold_name_0 = hold[i][0].substr(0,hold[i][0].find_last_of("."));
            string hold_name_1 = hold[i][1].substr(0,hold[i][1].find_last_of("."));
            if(hold[i][0].find("outpad") != string::npos)
                    hold_name_0 = "OUTPUT";
            if(hold[i][1].find("outpad") != string::npos)
                    hold_name_1 = "OUTPUT";
            if(hold[i][0].find("inpad") != string::npos)
                    hold_name_0 = "INPUT";
            if(hold[i][1].find("inpad") != string::npos)
                    hold_name_1 = "INPUT";
            inrslt << hold_name_0 << "\t" << hold_name_1 << "\t" << hold[i][2] << "\t" << hold[i][2] << "\n";
        }
        mark++;
    }
    inrslt << endl;
    inrslt.close();
    return true;

}

int main()
{
    printrsltfile("setup.out","hold.out","rsltfile");
    return 0;
}
