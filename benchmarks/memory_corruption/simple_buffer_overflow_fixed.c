// Caso correto: o vetor tem tamanho suficiente para o acesso ao indice 2.
#include <stdio.h>

int main(void) {
    int values[3] = {0, 1, 0};

    values[2] = 42;

    printf("%d\n", values[0]);
    return 0;
}
