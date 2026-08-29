enum mode {
    MODE_NONE = 0,
    MODE_READ = 1 << 0,
    MODE_WRITE = 1 << 1,
    MODE_BOTH = MODE_READ | MODE_WRITE
};

int main(void)
{
    enum mode value = MODE_BOTH;
    return value == 3 ? 0 : 1;
}
