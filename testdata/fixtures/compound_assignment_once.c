static int cursor;
static unsigned char values[3] = {255, 20, 30};

static int next_index(void)
{
    int index = cursor;
    cursor += 1;
    return index;
}

int main(void)
{
    values[next_index()] += 1;
    return cursor == 1 && values[0] == 0 && values[1] == 20 ? 0 : 1;
}
