enum wl_stat_t { none, block };

struct
{
    short picnum;
    wl_stat_t type;
    unsigned specialFlags;
} anonymous_records[2] = {
    {1},
    {2, block, 4}
};

int main()
{
    return anonymous_records[1].type == block && anonymous_records[1].specialFlags == 4 ? 0 : 1;
}
