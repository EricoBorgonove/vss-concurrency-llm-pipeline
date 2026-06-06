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
