#include <stdio.h>
#include <string.h>

int main(void)
{
    char buffer[32];
    strcpy(buffer, "elisa");
    snprintf(buffer, sizeof(buffer), "%s", buffer);
    return (int)strlen(buffer);
}
