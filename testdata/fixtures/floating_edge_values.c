#include <math.h>

int main(void)
{
    double negative_zero = -0.0;
    double quiet_nan = __builtin_nan("");
    double positive_infinity = __builtin_inf();
    double zero = 0.0;
    return negative_zero == 0.0 && negative_zero != 0.0 ? 1 :
           (NAN == NAN || INFINITY < 0.0 || quiet_nan == quiet_nan || positive_infinity < 0.0 ? 1 :
            (quiet_nan && !zero && positive_infinity ? 0 : 1));
}
