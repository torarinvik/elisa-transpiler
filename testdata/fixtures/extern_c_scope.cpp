extern "C" {
    int linkage_helper(int value)
    {
        return value + 5;
    }
}

int main()
{
    return linkage_helper(7) == 12 ? 0 : 1;
}
