static int promoted(unsigned char left, signed char right)
{
    return left + right;
}

int main(void)
{
    unsigned char left = 250;
    signed char right = -5;
    return promoted(left, right) == 245 ? 0 : 1;
}
