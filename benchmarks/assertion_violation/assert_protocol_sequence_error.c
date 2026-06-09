// Caso com erro: a sequencia de eventos nao abre o protocolo como o assert espera.
#include <assert.h>

enum protocol_state {
    CLOSED,
    OPENING,
    OPEN,
    CLOSING
};

static enum protocol_state step(enum protocol_state state, int event)
{
    if (state == CLOSED && event == 1) {
        return OPENING;
    }
    if (state == OPENING && event == 2) {
        return OPEN;
    }
    if (state == OPEN && event == 3) {
        return CLOSING;
    }
    return state;
}

int main(void)
{
    enum protocol_state state = CLOSED;

    state = step(state, 1);
    state = step(state, 3);

    assert(state == OPEN);
    return state;
}
