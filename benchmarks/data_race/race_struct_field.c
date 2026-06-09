// Caso com erro: deposit e withdraw alteram balance sem mutex.
#include <pthread.h>

struct account {
    int balance;
};

static struct account shared_account = {100};

static void *deposit(void *arg)
{
    (void)arg;
    shared_account.balance += 50;
    return NULL;
}

static void *withdraw(void *arg)
{
    (void)arg;
    shared_account.balance -= 30;
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, deposit, NULL);
    pthread_create(&t2, NULL, withdraw, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return shared_account.balance;
}
