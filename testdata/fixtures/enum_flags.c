enum mode {
    MODE_NONE = 0,
    MODE_READ = 0x01,
    MODE_WRITE = 0x04,
    MODE_BOTH = MODE_READ | MODE_WRITE
};

int main(void)
{
    enum mode value = MODE_BOTH;
    return value == 5 ? 0 : 1;
}
