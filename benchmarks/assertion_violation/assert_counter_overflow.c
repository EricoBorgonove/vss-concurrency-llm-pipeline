// Caso com erro: o contador chega a 5, mas o assert exige valor no maximo 3.
#include <assert.h>

int main(void)
{
    int counter = 0;

    for (int i = 0; i < 5; i++) {
        counter++;
    }

    assert(counter <= 3);
    return 0;
}
