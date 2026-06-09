// Caso com erro: strcpy copia "overflow" para target com apenas 5 bytes.
#include <string.h>

int main(void)
{
    char target[5];

    strcpy(target, "overflow");
    return target[0];
}
