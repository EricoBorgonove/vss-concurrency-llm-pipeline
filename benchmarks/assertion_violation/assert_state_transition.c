// Caso com erro: o estado salta para DONE, mas o assert espera READY.
#include <assert.h>

enum state {
    STATE_INIT,
    STATE_READY,
    STATE_DONE
};

int main(void)
{
    enum state current = STATE_INIT;

    current = STATE_DONE;
    assert(current == STATE_READY);
    return 0;
}
