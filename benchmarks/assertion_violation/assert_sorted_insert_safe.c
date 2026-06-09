// Caso correto: a insercao valida capacidade e o assert final confirma size == 5.
#include <assert.h>

static int insert_sorted(int values[], int size, int capacity, int value)
{
    int position = size;

    assert(size < capacity);
    while (position > 0 && values[position - 1] > value) {
        values[position] = values[position - 1];
        position--;
    }

    values[position] = value;
    return size + 1;
}

int main(void)
{
    int values[5] = {1, 3, 5, 7, 0};
    int size = 4;

    size = insert_sorted(values, size, 5, 6);

    assert(size == 5);
    return values[0];
}
