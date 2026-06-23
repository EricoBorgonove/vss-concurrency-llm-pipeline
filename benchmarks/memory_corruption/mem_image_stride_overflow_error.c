// Caso vulneravel: img usa tamanho derivado que ultrapassa o buffer.
#include <stdlib.h>

int main(void)
{
    int stride = 7;
    char pixels[16]; for (int row = 0; row < 3; ++row) for (int col = 0; col < stride; ++col) pixels[row * stride + col] = 1;
    return 0;
}
