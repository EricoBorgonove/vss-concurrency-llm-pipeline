// Caso vulneravel: seg usa tamanho derivado que ultrapassa o buffer.
#include <stdlib.h>

int main(void)
{
    
    char ring[10]; char *segment = ring + 6; for (int i = 0; i < 7; ++i) segment[i] = 'r';
    return 0;
}
