// Caso com erro: items[3] escreve fora do heap alocado para 3 inteiros.
#include <stdlib.h>

int main(void)
{
    int *items = malloc(3 * sizeof(int));
    if (items == NULL) {
        return 1;
    }

    items[3] = 42;
    free(items);
    return 0;
}
