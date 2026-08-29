#ifndef PROJECT_INCREMENT
#error project compile flags were not applied
#endif

int add_one(int value)
{
    return value + PROJECT_INCREMENT;
}
