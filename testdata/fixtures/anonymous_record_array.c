struct
{
    short picnum;
    int type;
    unsigned specialFlags;
} anonymous_records[2] = {
    {1},
    {2, 3, 4}
};

int main(void)
{
    return anonymous_records[1].type == 3 && anonymous_records[1].specialFlags == 4 ? 0 : 1;
}
