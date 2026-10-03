typedef int project_external_integer;

int project_external_sum(project_external_integer left, int right);
int project_external_qualified(const int value, int * const output);
int project_external_zero();

int project_external_alpha(void)
{
    int output = 0;
    return project_external_sum(19, 23)
        + project_external_qualified(5, &output)
        + output
        + project_external_zero();
}
