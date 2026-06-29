// Caso com erro: escrita concorrente usa limite desatualizado e ultrapassa o heap.
#include <pthread.h>
#include <stdlib.h>

static int *buffer;
static int tamanho = 2;

static void *gravador(void *arg)
{
    (void)arg;
    for (int i = 0; i < 10; i++) {
        buffer[i] = i;
    }
    return NULL;
}

int main(void)
{
    buffer = malloc((size_t)tamanho * sizeof(*buffer));
    if (buffer == NULL) {
        return 1;
    }

    pthread_t t1;
    pthread_create(&t1, NULL, gravador, NULL);
    tamanho = 20;
    buffer = realloc(buffer, (size_t)tamanho * sizeof(*buffer));
    pthread_join(t1, NULL);
    free(buffer);
    return 0;
}
