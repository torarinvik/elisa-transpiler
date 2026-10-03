int read_alpha_configuration(void);
int read_beta_configuration(void);
int read_alpha_shared_configuration(void);
int read_beta_shared_configuration(void);

int main()
{
    return read_alpha_configuration() == 17 && read_beta_configuration() == 29 && read_alpha_shared_configuration() == 43 && read_beta_shared_configuration() == 43 ? 0 : 1;
}
