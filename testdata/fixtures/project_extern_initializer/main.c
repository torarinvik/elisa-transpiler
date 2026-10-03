extern int initialized_project_value;
int initialized_project_value_read(void);

int main(void)
{
    return initialized_project_value == 37 && initialized_project_value_read() == 37 ? 0 : 1;
}
