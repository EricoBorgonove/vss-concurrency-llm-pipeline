// Caso vulneravel: auth usa tamanho derivado que ultrapassa o buffer.
#include <stdlib.h>

int main(void)
{
    
    char *token = malloc(4); if (!token) return 1; token[0]='a'; token[1]='b'; token[2]='c'; token[3]=0; int sum = 0; for (int i = 0; i < 9; ++i) sum += token[i]; free(token); return sum;
    return 0;
}
