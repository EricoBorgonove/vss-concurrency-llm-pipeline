#include <stdio.h>

int main(void) {
    int values[3] = {0, 1, 0};

    values[2] = 42;

    printf("%d\n", values[0]);
    return 0;
}
