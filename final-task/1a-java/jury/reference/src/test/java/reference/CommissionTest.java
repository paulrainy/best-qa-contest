package reference;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

class CommissionTest extends BaseTest {
    @Test
    void thresholdCrossingChargesOnlyExcess() throws Exception {
        var p = data.other();
        complete(start(p, "90000"));
        var t = complete(start(p, "20000"));
        assertThat(t.get("commission").decimalValue())
                .isEqualByComparingTo("100.00");
    }
    @ParameterizedTest
    @CsvSource({"10.00,30.00", "3456.78,34.57"})
    void minimumAndHalfUpAfterThreshold(String amount, String fee) throws Exception {
        var p = data.other();
        complete(start(p, "100000"));
        var t = complete(start(p, amount));
        money(fee, t.get("commission").decimalValue());
        money(new java.math.BigDecimal("900000")
                        .subtract(new java.math.BigDecimal(amount))
                        .subtract(new java.math.BigDecimal(fee))
                        .toPlainString(),
                api.balance(p.fromNumber()));
    }
}
