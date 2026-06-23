// Caso vulneravel: rotacao de token aceita geracao antiga como ativa.
void __ESBMC_assert(_Bool condition, const char *message);

struct session { int active_generation; int grace_generation; int presented_generation; };

static int authorize(struct session session)
{
    if (session.presented_generation == session.active_generation) return 1;
    if (session.presented_generation == session.grace_generation) return 1;
    return 0;
}

int main(void)
{
    struct session session = { .active_generation = 7, .grace_generation = 4, .presented_generation = 4 };
    int ok = authorize(session);
    __ESBMC_assert(!ok || session.presented_generation >= session.active_generation - 1, "accepted token generation must be recent");
    return 0;
}
