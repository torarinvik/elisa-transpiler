int project_forward_main(void);

int project_forward_value(int value)
{
    return value + 1;
}

int main(void)
{
    return project_forward_main() == 42 ? 0 : 1;
}
