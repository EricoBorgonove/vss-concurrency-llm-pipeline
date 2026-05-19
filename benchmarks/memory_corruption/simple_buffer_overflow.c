#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int *values = malloc(2 * sizeof(int));
    if (values == NULL) {
        return 1;
    }

    values[0] = 0;
    values[1] = 1;
    values[2] = 42;

    printf("%d\n", values[0]);
    free(values);
    return 0;
}
