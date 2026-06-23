// Caso vulneravel: pkt usa tamanho derivado que ultrapassa o buffer.
#include <stdlib.h>

int main(void)
{
    int first = 7; int second = 8;
    char packet[12]; for (int i = 0; i < first + second; ++i) packet[i] = 'p';
    return 0;
}
