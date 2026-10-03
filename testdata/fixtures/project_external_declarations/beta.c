int project_external_sum(int first, int second);
int project_external_qualified(int value, int *output);
int project_external_zero(void);

int project_external_beta(void)
{
    int output = 0;
    return project_external_sum(1, 2)
        + project_external_qualified(8, &output)
        + output
        + project_external_zero();
}
