static int cursor;
static unsigned char values[3] = {255, 20, 30};
static _Bool flag;

static int next_index(void)
{
    int index = cursor;
    cursor += 1;
    return index;
}

static int identity(int value)
{
    return value;
}

static int postfix_from_return(void)
{
    return cursor++;
}

int main(void)
{
    int value = cursor++;
    if (value != 0 || cursor != 1)
        return 1;

    cursor = 4;
    value = ++cursor;
    if (value != 5 || cursor != 5)
        return 2;

    cursor = 0;
    unsigned char old_value = values[next_index()]++;
    if (cursor != 1 || old_value != 255 || values[0] != 0)
        return 3;

    cursor = 0;
    values[0] = 255;
    unsigned char new_value = ++values[next_index()];
    if (cursor != 1 || new_value != 0 || values[0] != 0)
        return 4;

    cursor = 0;
    value = 40 + cursor++;
    if (value != 40 || cursor != 1)
        return 5;

    cursor = 9;
    value = identity(cursor++);
    if (value != 9 || cursor != 10)
        return 6;

    cursor = 11;
    value = identity(++cursor);
    if (value != 12 || cursor != 12)
        return 9;

    cursor = 2;
    if (cursor-- != 2 || cursor != 1)
        return 10;
    if (--cursor != 0 || cursor != 0)
        return 11;

    float fraction = 1.5f;
    float old_fraction = fraction++;
    if (old_fraction != 1.5f || fraction != 2.5f)
        return 12;
    fraction = 2.5f;
    float new_fraction = --fraction;
    if (new_fraction != 1.5f || fraction != 1.5f)
        return 13;

    flag = 0;
    if (flag++ != 0 || !flag)
        return 14;
    if (--flag || flag)
        return 15;

    cursor = 3;
    if (cursor++ != 3 || cursor != 4)
        return 7;

    cursor = 11;
    value = postfix_from_return();
    if (value != 11 || cursor != 12)
        return 8;

    return 0;
}
