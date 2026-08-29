struct Pair {
    int first;
    int second;
    int third;
};

static struct Pair pair = { .second = 7, .first = 3 };
static int values[5] = { [2] = 7, [4] = 9 };

int main(void)
{
    return pair.first == 3 && pair.second == 7 && pair.third == 0 && values[0] == 0 && values[2] == 7 && values[4] == 9 ? 0 : 1;
}
