// Caso correto: value satisfaz a assercao esperada pelo ESBMC.
void __ESBMC_assert(int condition, const char *message);

int main(void) {
    int value = 1;

    __ESBMC_assert(value == 1, "value should be one");

    return 0;
}
