#include <string.h>

struct token {
    char text[8];
};

static void parse_token(struct token *token, const char *input)
{
    strncpy(token->text, input, sizeof(token->text) - 1);
    token->text[sizeof(token->text) - 1] = '\0';
}

int main(void)
{
    struct token token;

    parse_token(&token, "concurrency");
    return token.text[0];
}
