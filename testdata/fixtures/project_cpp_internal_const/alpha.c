const int project_configuration = 17;
extern const int shared_configuration;
const int shared_configuration = 43;

int read_alpha_configuration(void)
{
    return project_configuration;
}

int read_alpha_shared_configuration(void)
{
    return shared_configuration;
}
