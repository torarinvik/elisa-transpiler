int project_identity_first(void);
int project_identity_second(void);
int project_identity_hyphen_value(void);
int project_identity_underscore_value(void);

int main(void)
{
    return project_identity_first() + project_identity_second() +
        project_identity_hyphen_value() + project_identity_underscore_value() == 66 ? 0 : 1;
}
