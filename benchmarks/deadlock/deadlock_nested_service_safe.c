#include <pthread.h>
#include <unistd.h>

struct service {
    pthread_mutex_t state_lock;
    pthread_mutex_t metrics_lock;
};

static struct service service = {
    PTHREAD_MUTEX_INITIALIZER,
    PTHREAD_MUTEX_INITIALIZER
};

static void lock_service(void)
{
    pthread_mutex_lock(&service.state_lock);
    usleep(1000);
    pthread_mutex_lock(&service.metrics_lock);
}

static void unlock_service(void)
{
    pthread_mutex_unlock(&service.metrics_lock);
    pthread_mutex_unlock(&service.state_lock);
}

static void *update_state(void *arg)
{
    (void)arg;
    lock_service();
    unlock_service();
    return NULL;
}

static void *collect_metrics(void *arg)
{
    (void)arg;
    lock_service();
    unlock_service();
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, update_state, NULL);
    pthread_create(&t2, NULL, collect_metrics, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return 0;
}
