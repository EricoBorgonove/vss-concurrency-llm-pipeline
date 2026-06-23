// Caso vulneravel: atualizacao concorrente de estado compartilhado sem mutex.
#include <pthread.h>

static int flag_enabled = 0; static int rollout = 0;
static void *worker(void *arg){ int value=*(int*)arg; rollout = value; flag_enabled = value > 10; return 0; }

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
