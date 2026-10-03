#define API(ReturnType) ReturnType

static int earlier_source_function(void)
{
    return 0;
}

API(int) exported_api_value(void)
{
    return 42;
}
