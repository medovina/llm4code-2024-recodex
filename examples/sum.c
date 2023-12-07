#include <stdio.h>
#include <stdlib.h>

int main() {
    char line[30];

    fgets(line, sizeof line, stdin);
    int i = atoi(line);
    fgets(line, sizeof line, stdin);
    int j = atoi(line);

    printf("%d\n", i + j);
    return 0;
}
