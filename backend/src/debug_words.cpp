#include <iostream>
#include <fstream>
#include <string>
using namespace std;

int main() {
    ifstream f("words.txt");
    if (!f.is_open()) {
        cout << "FAILED to open words.txt!" << endl;
        // Try absolute path or parent dir path
        ifstream f2("backend/src/words.txt");
        if (f2.is_open()) {
            cout << "SUCCEEDED with backend/src/words.txt" << endl;
        } else {
            cout << "FAILED with backend/src/words.txt too!" << endl;
        }
    } else {
        cout << "SUCCESS! Opened words.txt successfully." << endl;
        string line;
        int count = 0;
        while (getline(f, line)) {
            count++;
            if (count <= 5) {
                cout << "Line " << count << ": " << line << endl;
            }
        }
        cout << "Total lines: " << count << endl;
    }
    return 0;
}
