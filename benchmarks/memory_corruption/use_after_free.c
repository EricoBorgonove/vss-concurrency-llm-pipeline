// Caso com erro: value e usado depois de free(value).
#include <stdlib.h>

int main(void)
{
    int *value = malloc(sizeof(int));
    if (value == NULL) {
        return 1;
    }

    *value = 10;
    free(value);
    *value = 20;
    return 0;
}
