static inline unsigned short readword(unsigned char *&ptr)
{
    unsigned short value = ptr[0] | ptr[1] << 8;
    ptr += 2;
    return value;
}

int main()
{
    unsigned char bytes[4] = {0};
    bytes[0] = 0x34;
    bytes[1] = 0x12;
    bytes[2] = 0x78;
    bytes[3] = 0x56;
    unsigned char *ptr = bytes;
    unsigned short first = readword(ptr);
    unsigned short second = readword(ptr);
    return first == 0x1234 && second == 0x5678 && ptr == bytes + 4 ? 0 : 1;
}
