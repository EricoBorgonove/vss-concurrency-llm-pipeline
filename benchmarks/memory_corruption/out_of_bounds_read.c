// Caso com erro: values[2] le fora do vetor com indices 0..1.
#include <stdio.h>

int main(void)
{
    int values[2] = {10, 20};

    printf("%d\n", values[2]);
    return 0;
}
