// Caso vulneravel: tlv usa tamanho derivado que ultrapassa o buffer.
#include <stdlib.h>

int main(void)
{
    int len = 12;
    unsigned char buf[8]; for (int i = 0; i <= len; ++i) buf[i] = (unsigned char)i;
    return 0;
}
