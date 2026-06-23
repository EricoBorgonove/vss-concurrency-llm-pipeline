// Caso vulneravel: vec usa tamanho derivado que ultrapassa o buffer.
#include <stdlib.h>

int main(void)
{
    int count = 4;
    int *items = malloc(sizeof(int) * 4); if (!items) return 1; for (int i = 0; i <= count; ++i) items[i] = i; int r = items[0]; free(items); return r;
    return 0;
}
