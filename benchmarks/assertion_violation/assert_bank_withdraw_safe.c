#include <assert.h>

struct account {
    int balance;
    int limit;
};

static int withdraw(struct account *account, int value)
{
    if (account->balance - value < -account->limit) {
        return 0;
    }

    account->balance -= value;
    return 1;
}

int main(void)
{
    struct account account = {100, 40};
    int accepted = withdraw(&account, 150);

    assert(accepted == 0);
    assert(account.balance >= -account.limit);
    return account.balance;
}
