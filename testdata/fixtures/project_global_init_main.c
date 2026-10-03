extern int project_global_init_value;

int main(void)
{
    return project_global_init_value == 41 ? 0 : 1;
}
