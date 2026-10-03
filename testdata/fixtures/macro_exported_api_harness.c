int exported_api_value(void);

int main(void)
{
    return exported_api_value() == 42 ? 0 : 1;
}
