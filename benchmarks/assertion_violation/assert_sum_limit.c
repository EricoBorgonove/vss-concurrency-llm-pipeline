// Caso com erro: a soma vale 15, mas o assert exige valor menor que 10.
#include <assert.h>

int main(void)
{
    int a = 7;
    int b = 8;
    int sum = a + b;

    assert(sum < 10);
    return 0;
}
