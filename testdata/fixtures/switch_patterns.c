enum token {
    TOKEN_ZERO = 0,
    TOKEN_ONE = 1,
    TOKEN_OTHER = 9
};

static int dense(int value)
{
    switch (value)
    {
        case 10:
        case 11:
        case 12:
            return 100;
        case 20:
            return 200;
        default:
            return -1;
    }
}

static int symbolic(enum token value)
{
    switch (value)
    {
        case TOKEN_ZERO:
        case TOKEN_ONE:
            return 10;
        case TOKEN_OTHER:
            return 20;
        default:
            return -1;
    }
}

int main(void)
{
    return dense(10) == 100 && dense(11) == 100 && dense(12) == 100 && dense(13) == -1 && dense(20) == 200 && symbolic(TOKEN_ZERO) == 10 && symbolic(TOKEN_ONE) == 10 && symbolic(TOKEN_OTHER) == 20 ? 0 : 1;
}
