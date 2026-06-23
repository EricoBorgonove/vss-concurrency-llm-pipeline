// Caso vulneravel: janela de credito reabre mais limite do que o permitido.
void __ESBMC_assert(_Bool condition, const char *message);

struct credit_window { int used; int recovered; int hard_limit; int reopened; };

static struct credit_window decay_window(struct credit_window window)
{
    if (window.recovered > 0) {
        window.reopened = window.hard_limit - window.used + window.recovered;
    }
    return window;
}

int main(void)
{
    struct credit_window window = { .used = 70, .recovered = 45, .hard_limit = 100, .reopened = 0 };
    window = decay_window(window);
    __ESBMC_assert(window.reopened <= window.hard_limit - window.used, "reopened credit must not exceed available window");
    return 0;
}
