// Codigo aleatorio: deve acionar ESBMC pela presenca de assert.
#include <assert.h>

int main(void)
{
    int value = 2;

    assert(value == 1);
    return value;
}
