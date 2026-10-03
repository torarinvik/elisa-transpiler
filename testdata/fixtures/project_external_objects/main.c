int project_external_alpha(void);
int project_external_beta(void);

int main(void)
{
    return project_external_alpha() == 39 && project_external_beta() == 42 ? 0 : 1;
}
