// Caso vulneravel: blk usa tamanho derivado que ultrapassa o buffer.
#include <stdlib.h>

int main(void)
{
    int compressed = 8; int header = 5;
    char block[10]; for (int i = 0; i < compressed + header; ++i) block[i] = 'Z';
    return 0;
}
