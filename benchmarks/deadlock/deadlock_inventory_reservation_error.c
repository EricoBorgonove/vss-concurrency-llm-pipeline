// Caso vulneravel: duas threads adquirem stock_lock e reservation_lock em ordem oposta.
#include <pthread.h>
#include <unistd.h>

static pthread_mutex_t stock_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t reservation_lock = PTHREAD_MUTEX_INITIALIZER;

static void *first_path(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&stock_lock);
    usleep(1000);
    pthread_mutex_lock(&reservation_lock);
    pthread_mutex_unlock(&reservation_lock);
    pthread_mutex_unlock(&stock_lock);
    return 0;
}

static void *second_path(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&reservation_lock);
    usleep(1000);
    pthread_mutex_lock(&stock_lock);
    pthread_mutex_unlock(&stock_lock);
    pthread_mutex_unlock(&reservation_lock);
    return 0;
}

int main(void)
{
    pthread_t a, b;
    pthread_create(&a, 0, first_path, 0);
    pthread_create(&b, 0, second_path, 0);
    pthread_join(a, 0);
    pthread_join(b, 0);
    return 0;
}
