// Caso com erro: value e negativo e viola o assert value >= 0.
#include <assert.h>

int main(void)
{
    int value = -1;

    assert(value >= 0);
    return 0;
}
