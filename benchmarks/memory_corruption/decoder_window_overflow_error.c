// Caso vulneravel: janela calculada a partir de deslocamento ultrapassa buffer.
#include <stdlib.h>
#include <string.h>

struct decoder {
    char window[16];
    int offset;
};

static void append_chunk(struct decoder *decoder, const char *chunk)
{
    int start = decoder->offset;
    for (int i = 0; chunk[i] != '\0'; ++i) {
        decoder->window[start + i] = chunk[i];
    }
}

int main(void)
{
    struct decoder *decoder = malloc(sizeof(*decoder));
    if (!decoder) {
        return 1;
    }

    memset(decoder->window, 0, sizeof(decoder->window));
    decoder->offset = 14;
    append_chunk(decoder, "payload-window-overflow");

    int result = decoder->window[0];
    free(decoder);
    return result;
}
