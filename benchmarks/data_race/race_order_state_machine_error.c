// Caso vulneravel: atualizacao concorrente de estado compartilhado sem mutex.
#include <pthread.h>

static int state = 0;
static void *worker(void *arg){ int next=*(int*)arg; if (state < next) state = next; return 0; }

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
