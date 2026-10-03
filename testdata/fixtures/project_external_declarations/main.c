int project_external_alpha(void);
int project_external_beta(void);

int main(void)
{
    return project_external_alpha() == 70 && project_external_beta() == 37 ? 0 : 1;
}
