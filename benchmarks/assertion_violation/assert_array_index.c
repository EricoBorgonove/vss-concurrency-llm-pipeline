// Caso com erro: o assert falha porque index vale 4 e o vetor tem indices 0..2.
#include <assert.h>

int main(void)
{
    int values[3] = {1, 2, 3};
    int index = 4;

    assert(index >= 0 && index < 3);
    return values[index];
}
