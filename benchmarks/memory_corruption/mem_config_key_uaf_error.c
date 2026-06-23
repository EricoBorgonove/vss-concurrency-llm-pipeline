// Caso vulneravel: uaf usa tamanho derivado que ultrapassa o buffer.
#include <stdlib.h>

int main(void)
{
    
    char *key = malloc(8); if (!key) return 1; key[0] = 'a'; free(key); key[1] = 'b'; return key[0];
    return 0;
}
