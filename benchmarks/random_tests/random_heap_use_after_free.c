// Codigo aleatorio: deve acionar ASAN e AFL por uso de memoria dinamica.
#include <stdlib.h>

int main(void)
{
    int *value = malloc(sizeof(int));

    if (value == NULL) {
        return 1;
    }

    *value = 42;
    free(value);
    return *value;
}
