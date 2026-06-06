#include <stdio.h>

int main(void)
{
    char buffer[4] = {'a', 'b', 'c', '\0'};

    buffer[4] = 'x';
    puts(buffer);
    return 0;
}
