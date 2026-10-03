const int project_configuration = 29;
extern const int shared_configuration;

int read_beta_configuration(void)
{
    return project_configuration;
}

int read_beta_shared_configuration(void)
{
    return shared_configuration;
}
