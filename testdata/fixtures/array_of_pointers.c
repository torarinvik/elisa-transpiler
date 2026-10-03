static int first_plane[4] = {10, 11, 12, 13};
static int second_plane[4] = {20, 21, 22, 23};
static int *planes[2] = {first_plane, second_plane};

int main(void)
{
    return planes[1][2] == 22 && planes[0][3] == 13 ? 0 : 1;
}
