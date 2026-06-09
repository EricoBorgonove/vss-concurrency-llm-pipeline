#include <pthread.h>
#include <unistd.h>

static pthread_mutex_t cache_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t database_lock = PTHREAD_MUTEX_INITIALIZER;

static void lock_cache_and_database(void)
{
    pthread_mutex_lock(&cache_lock);
    usleep(1000);
    pthread_mutex_lock(&database_lock);
}

static void unlock_cache_and_database(void)
{
    pthread_mutex_unlock(&database_lock);
    pthread_mutex_unlock(&cache_lock);
}

static void *refresh_cache(void *arg)
{
    (void)arg;
    lock_cache_and_database();
    unlock_cache_and_database();
    return NULL;
}

static void *write_database(void *arg)
{
    (void)arg;
    lock_cache_and_database();
    unlock_cache_and_database();
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
