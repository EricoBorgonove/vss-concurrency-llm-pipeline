// Caso vulneravel: janela deslizante conserva eventos expirados.
void __ESBMC_assert(_Bool condition, const char *message);

static int count_window(int events[5], int now, int window)
{
    int count = 0;
    for (int i = 0; i < 5; ++i) {
        if (now - events[i] <= window + 1) count += 1;
    }
    return count;
}

int main(void)
{
    int events[5] = { 90, 91, 92, 99, 100 };
    int visible = count_window(events, 100, 8);
    __ESBMC_assert(visible <= 2, "rate limiter must discard expired events");
    return 0;
}
