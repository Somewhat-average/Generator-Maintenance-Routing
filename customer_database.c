#include <stdio.h>

int main(void)
{
    char buf[32];
    printf("Enter string: ");
    fgets(buf, 32, stdin);
    printf("buf: %s", buf);
}
