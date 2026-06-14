// Caso vulneravel: transferencia entre particoes pode travar por ordem derivada.
#include <pthread.h>
#include <unistd.h>

struct partition {
    pthread_mutex_t lock;
    int balance;
};

static struct partition partitions[2] = {
    { PTHREAD_MUTEX_INITIALIZER, 10 },
    { PTHREAD_MUTEX_INITIALIZER, 20 },
};

static void transfer(int from, int to, int amount)
{
    pthread_mutex_lock(&partitions[from].lock);
    usleep(1000);
    pthread_mutex_lock(&partitions[to].lock);

    partitions[from].balance -= amount;
    partitions[to].balance += amount;

    pthread_mutex_unlock(&partitions[to].lock);
    pthread_mutex_unlock(&partitions[from].lock);
}

static void *move_forward(void *arg)
{
    (void)arg;
    transfer(0, 1, 1);
    return 0;
}

static void *move_backward(void *arg)
{
    (void)arg;
    transfer(1, 0, 1);
    return 0;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, 0, move_forward, 0);
    pthread_create(&t2, 0, move_backward, 0);
    pthread_join(t1, 0);
    pthread_join(t2, 0);
    return partitions[0].balance + partitions[1].balance;
}
