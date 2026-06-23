// Caso vulneravel: csv usa tamanho derivado que ultrapassa o buffer.
#include <stdlib.h>

int main(void)
{
    int width = 9;
    char field[6]; for (int i = 0; i <= width; ++i) field[i] = 'c';
    return 0;
}
