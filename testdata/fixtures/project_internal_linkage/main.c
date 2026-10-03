int project_internal_alpha(void);
int project_internal_beta(void);

int main(void)
{
    return project_internal_alpha() + project_internal_beta() == 83 ? 0 : 1;
}
