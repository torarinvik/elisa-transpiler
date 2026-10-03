typedef struct Objstruct
{
    int value;
} objtype;

objtype *actorat[4][4];

void take_rows(objtype *(*rows)[4])
{
    (void)rows;
}

int main(void)
{
    take_rows(actorat);
    return 0;
}
