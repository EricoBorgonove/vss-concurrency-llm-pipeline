void __ESBMC_assert(int condition, const char *message);

int main(void) {
    int value = 0;

    __ESBMC_assert(value == 1, "value should be one");

    return 0;
}
