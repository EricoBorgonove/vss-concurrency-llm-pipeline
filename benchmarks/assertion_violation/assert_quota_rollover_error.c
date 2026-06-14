// Caso vulneravel: rollover condicional ultrapassa a cota maxima permitida.
void __ESBMC_assert(_Bool condition, const char *message);

struct account_quota {
    int used;
    int carry;
    int limit;
};

static int apply_rollover(struct account_quota quota)
{
    int available = quota.limit - quota.used;
    if (quota.carry > available) {
        quota.used += quota.carry;
    } else {
        quota.used += available;
    }
    return quota.used;
}

int main(void)
{
    struct account_quota quota = { .used = 8, .carry = 5, .limit = 10 };
    int final_usage = apply_rollover(quota);

    __ESBMC_assert(final_usage <= quota.limit, "usage must respect quota limit");
    return 0;
}
