struct Sample
{
    int value;
};

static int read_values(unsigned char *byte, int *number, struct Sample *sample, char **text)
{
    return *byte + *number + sample->value + (*text)[0];
}

int main(void)
{
    unsigned char byte = 2;
    int number = 3;
    struct Sample sample = { 4 };
    char *text = "A";
    return read_values(&byte, &number, &sample, &text) == 74 ? 0 : 1;
}
