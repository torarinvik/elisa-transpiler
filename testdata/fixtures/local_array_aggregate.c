int main(void)
{
    int record[6] = { 7, 11, 13, 17, 19, 23 };
    return record[0] == 7 && record[1] == 11 && record[2] == 13 &&
           record[3] == 17 && record[4] == 19 && record[5] == 23 ? 0 : 1;
}
