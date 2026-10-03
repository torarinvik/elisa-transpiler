int project_choose(int value);
int project_choose(float value);
int project_choose(double value);
int project_choose(long value);

int main()
{
    short small = 1;
    if (project_choose(1) != 11) return 1;
    if (project_choose(1.0) != 21) return 2;
    if (project_choose(1.0f) != 31) return 3;
    if (project_choose(small) != 11) return 4;
    return 0;
}
