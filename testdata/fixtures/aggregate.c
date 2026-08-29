// A small aggregate exercises C's implicit zero initialization.
struct Pair {
    int first;
    int second;
    int third;
};

// The translator should preserve this declaration's source context.
int main(void)
{
    struct Pair pair = { 7 };
    return pair.first == 7 && pair.second == 0 && pair.third == 0 ? 0 : 1;
}
