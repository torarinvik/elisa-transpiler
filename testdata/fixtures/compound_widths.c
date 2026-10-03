struct Pair
{
    int total;
    unsigned char byte;
};

int main(void)
{
    int total = 10;
    short delta = 5;
    unsigned char small = 2;
    total += delta;
    total += small;

    unsigned char byte = 250;
    int wide = 7;
    byte += wide;

    struct Pair pair = {10, 250};
    pair.total += delta;
    pair.byte += total;
    return total == 17 && byte == 1 && pair.total == 15 && pair.byte == 11 ? 0 : 1;
}
