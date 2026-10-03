typedef unsigned char byte;

int main(void)
{
    byte data[450];
    return sizeof(data) == 450 ? 0 : 1;
}
