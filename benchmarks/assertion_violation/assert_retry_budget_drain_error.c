// Caso vulneravel: drenagem de tentativas fica negativa apos penalidades encadeadas.
void __ESBMC_assert(_Bool condition, const char *message);

static int apply_retry_policy(int budget, int transient_failures, int permanent_failures)
{
    for (int i = 0; i < transient_failures; ++i) budget -= 1;
    for (int i = 0; i < permanent_failures; ++i) budget -= 3;
    return budget;
}

int main(void)
{
    int remaining = apply_retry_policy(8, 3, 3);
    __ESBMC_assert(remaining >= 0, "retry budget must never be negative");
    return 0;
}
