typedef struct BitfieldFlags {
    unsigned int enabled : 1;
    unsigned int mode : 3;
} BitfieldFlags;

int main(void)
{
    BitfieldFlags flags = {0};
    flags.enabled = 1;
    flags.mode = 5;
    return flags.enabled && flags.mode == 5 ? 0 : 1;
}
