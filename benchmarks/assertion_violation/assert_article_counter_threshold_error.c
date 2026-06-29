// Caso com erro: check-then-increment concorrente permite ultrapassar limite.
#include <assert.h>
#include <pthread.h>
#include <unistd.h>

static int total_pedidos = 0;

static void *gerar_pedido(void *arg)
{
    (void)arg;
    if (total_pedidos < 1) {
        usleep(1000);
        total_pedidos++;
    }
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, gerar_pedido, NULL);
    pthread_create(&t2, NULL, gerar_pedido, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    assert(total_pedidos <= 1);
    return 0;
}
