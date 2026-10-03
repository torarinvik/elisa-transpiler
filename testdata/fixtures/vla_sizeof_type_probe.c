int main(void)
{
    int count = 3;
    int bytes = sizeof(int[count++]);
    return count == 4 && bytes == 3 * (int)sizeof(int) ? 0 : 1;
}
