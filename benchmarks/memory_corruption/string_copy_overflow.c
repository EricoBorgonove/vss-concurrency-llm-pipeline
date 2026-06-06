#include <string.h>

int main(void)
{
    char target[5];

    strcpy(target, "overflow");
    return target[0];
}
