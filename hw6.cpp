#include <iostream>
using namespace std;

void foo(int x)
{
    try
    {
        try
        {
            switch (x)
            {
            case 0:
                throw range_error("out of range error");
            case 1:
                throw invalid_argument("invalid_argument");
            case 2:
                throw logic_error("invalid_argument");
            case 3:
                throw bad_exception();
            case 4:
                break;
            }
        }
        catch (logic_error &le)
        {
            cout << "catch 1\n";
        }
        cout << "hurray!\n";
    }
    catch (runtime_error &re)
    {
        cout << "catch 2\n";
    }
    cout << "I'm done!\n";
}

void bar(int x)
{
    try
    {
        foo(x);
        cout << "that's what I say\n";
    }
    catch (exception &e)
    {
        cout << "catch 3\n";
        return;
    }
    cout << "Really done!\n";
}

int main()
{
    bar(3);
}