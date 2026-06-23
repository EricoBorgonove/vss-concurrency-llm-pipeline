// Caso vulneravel: atualizacao concorrente de estado compartilhado sem mutex.
#include <pthread.h>

static int free_slots = 5;
static void *worker(void *arg){ (void)arg; if (free_slots > 0) free_slots--; return 0; }

int main(void)
{
    pthread_t a, b;
    int x = 3;
    int y = 7;
    pthread_create(&a, 0, worker, &x);
    pthread_create(&b, 0, worker, &y);
    pthread_join(a, 0);
    pthread_join(b, 0);
    return 0;
}
