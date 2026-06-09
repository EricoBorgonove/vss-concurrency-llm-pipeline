#include <string.h>

struct token {
    char text[8];
};

static void parse_token(struct token *token, const char *input)
{
    strcpy(token->text, input);
}

int main(void)
{
    struct token token;

    parse_token(&token, "concurrency");
    return token.text[0];
}
