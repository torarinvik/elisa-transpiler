#include <math.h>

int main(void)
{
    double negative_zero = -0.0;
    double quiet_nan = __builtin_nan("");
    double positive_infinity = __builtin_inf();
    double zero = 0.0;
    float decimal_just_above_f32_midpoint = 1.000000059604644775390626f;
    float smallest_f32_subnormal = 0x1p-149f;
    double decimal_f64_nearest = 0.10000000000000001;
    double smallest_f64_subnormal = 0x1p-1074;

    if (decimal_just_above_f32_midpoint != 0x1.000002p0f ||
        smallest_f32_subnormal == 0.0f ||
        decimal_f64_nearest != 0x1.999999999999ap-4 ||
        smallest_f64_subnormal == 0.0) {
        return 2;
    }

    return negative_zero == 0.0 && negative_zero != 0.0 ? 1 :
           (NAN == NAN || INFINITY < 0.0 || quiet_nan == quiet_nan || positive_infinity < 0.0 ? 1 :
            (quiet_nan && !zero && positive_infinity ? 0 : 1));
}
