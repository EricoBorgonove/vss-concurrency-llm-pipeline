#include <pthread.h>
#include <unistd.h>

static pthread_mutex_t cache_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t database_lock = PTHREAD_MUTEX_INITIALIZER;

static void *refresh_cache(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&cache_lock);
    usleep(1000);
    pthread_mutex_lock(&database_lock);
    return NULL;
}

static void *write_database(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&database_lock);
    usleep(1000);
    pthread_mutex_lock(&cache_lock);
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, refresh_cache, NULL);
    pthread_create(&t2, NULL, write_database, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return 0;
}
