int project_choose(int value)
{
    return value + 10;
}

int project_choose(float value)
{
    return static_cast<int>(value) + 30;
}

int project_choose(double value)
{
    return static_cast<int>(value) + 20;
}

int project_choose(long value)
{
    return static_cast<int>(value) + 40;
}
