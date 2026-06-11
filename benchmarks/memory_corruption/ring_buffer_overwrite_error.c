// Caso com erro: write_index cresce sem modulo e escreve fora do ring buffer.
#include <stdio.h>
#include <stdlib.h>

struct ring_buffer {
    int *data;
    int write_index;
};

static void push(struct ring_buffer *buffer, int value)
{
    buffer->data[buffer->write_index] = value;
    buffer->write_index++;
}

int main(void)
{
    struct ring_buffer buffer = {malloc(4 * sizeof(int)), 0};
    if (buffer.data == NULL) {
        return 1;
    }

    for (int i = 0; i < 5; i++) {
        push(&buffer, i);
    }

    printf("%d\n", buffer.data[0]);
    free(buffer.data);
    return 0;
}
