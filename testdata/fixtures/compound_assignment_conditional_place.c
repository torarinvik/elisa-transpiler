struct Entry
{
    int value;
};

static int place_effects;
static int value_effects;
static struct Entry entries[2] = {{10}, {20}};

static int mark_place(void)
{
    ++place_effects;
    return 0;
}

static int mark_value(void)
{
    ++value_effects;
    return 0;
}

int main(void)
{
    int selector = 1;
    entries[selector ? (mark_place(), 0) : (mark_place(), 1)].value += 3;
    entries[0].value += selector ? (mark_value(), 2) : (mark_value(), 3);
    if (entries[0].value != 15 || entries[1].value != 20 || place_effects != 1 || value_effects != 1) {
        return 1;
    }

    selector = 0;
    int result = entries[selector ? (mark_place(), 0) : (mark_place(), 1)].value += selector ? (mark_value(), 4) : (mark_value(), 5);
    if (result != 25 || entries[0].value != 15 || entries[1].value != 25 || place_effects != 2 || value_effects != 2) {
        return 2;
    }
    return 0;
}
