#include <iostream>

int main() {
    std::string line;

    std::getline(std::cin, line);
    int x = stoi(line);

    std::getline(std::cin, line);
    int y = stoi(line);

    std::cout << x + y << std::endl;
    return 0;
}
