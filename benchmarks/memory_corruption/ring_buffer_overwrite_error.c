#include <stdio.h>

struct ring_buffer {
    int data[4];
    int write_index;
};

static void push(struct ring_buffer *buffer, int value)
{
    buffer->data[buffer->write_index] = value;
    buffer->write_index++;
}

int main(void)
{
    struct ring_buffer buffer = {{0, 0, 0, 0}, 0};

    for (int i = 0; i < 5; i++) {
        push(&buffer, i);
    }

    printf("%d\n", buffer.data[0]);
    return 0;
}
