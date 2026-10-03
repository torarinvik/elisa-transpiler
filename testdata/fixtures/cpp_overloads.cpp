int choose(int value)
{
    return value + 10;
}

int choose(double value)
{
    return static_cast<int>(value) + 20;
}

int choose(float value)
{
    return static_cast<int>(value) + 30;
}

int choose(long value)
{
    return static_cast<int>(value) + 40;
}

int main()
{
    short small = 1;
    return choose(1) == 11 && choose(1.0) == 21 &&
                   choose(1.0f) == 31 && choose(small) == 11
               ? 0
               : 1;
}
