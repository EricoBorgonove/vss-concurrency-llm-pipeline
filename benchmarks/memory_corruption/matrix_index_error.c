// Caso com erro: read_cell(3, 1) acessa linha fora da matriz 3x3.
#include <stdio.h>

static int read_cell(int row, int column)
{
    int matrix[3][3] = {
        {1, 2, 3},
        {4, 5, 6},
        {7, 8, 9}
    };

    return matrix[row][column];
}

int main(void)
{
    printf("%d\n", read_cell(3, 1));
    return 0;
}
