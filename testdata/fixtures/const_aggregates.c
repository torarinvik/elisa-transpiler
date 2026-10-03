struct const_configuration
{
    int magic;
    char tag[4];
};

static const int const_numbers[3] = {1, 0, 3};
static const struct const_configuration const_configuration = {7, {'E', 'L', 'I', 'S'}};
static const char *const_names[2] = {"alpha", "beta"};

int main(void)
{
    return const_numbers[0] + const_numbers[2] == 4 &&
        const_configuration.magic == 7 &&
        const_configuration.tag[0] == 'E' &&
        const_names[1][0] == 'b' ? 0 : 1;
}
