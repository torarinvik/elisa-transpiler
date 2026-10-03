int matrix[4][2] = {{0, -1}, {1, 0}, {0, 1}, {-1, 0}};

struct Cell
{
    int value;
};

struct Cell cells[2][2] = {{{1}, {2}}, {{3}, {4}}};

static int lookup(int row, int column)
{
    return matrix[row][column];
}

int main(void)
{
    return lookup(2, 1) == 1 && cells[1][0].value == 3 ? 0 : 1;
}
