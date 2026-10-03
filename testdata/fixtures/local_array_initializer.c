int main(void)
{
    char value[8] = "foo";
    return value[0] == 'f' && value[1] == 'o' && value[2] == 'o' && value[3] == 0 ? 0 : 1;
}
