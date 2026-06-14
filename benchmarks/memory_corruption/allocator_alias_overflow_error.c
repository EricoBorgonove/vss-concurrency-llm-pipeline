// Caso vulneravel: alias interno permite escrita alem do bloco alocado.
#include <stdlib.h>

struct packet {
    int header;
    char payload[8];
};

static void fill_payload(struct packet *packet, int length)
{
    char *cursor = packet->payload;
    for (int i = 0; i <= length; ++i) {
        cursor[i] = (char)('A' + (i % 26));
    }
}

int main(void)
{
    struct packet *packet = malloc(sizeof(*packet));
    if (!packet) {
        return 1;
    }

    packet->header = 7;
    fill_payload(packet, 12);

    int result = packet->payload[0];
    free(packet);
    return result;
}
