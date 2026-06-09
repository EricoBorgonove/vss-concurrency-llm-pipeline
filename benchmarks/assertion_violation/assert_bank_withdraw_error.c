#include <assert.h>

struct account {
    int balance;
    int limit;
};

static void withdraw(struct account *account, int value)
{
    account->balance -= value;
}

int main(void)
{
    struct account account = {100, 40};

    withdraw(&account, 150);

    assert(account.balance >= -account.limit);
    return account.balance;
}
