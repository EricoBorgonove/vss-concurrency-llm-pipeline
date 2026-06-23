// Caso vulneravel: utf usa tamanho derivado que ultrapassa o buffer.
#include <stdlib.h>

int main(void)
{
    int chars = 4; int expansion = 3;
    char normalized[8]; for (int i = 0; i < chars * expansion; ++i) normalized[i] = 'u';
    return 0;
}
