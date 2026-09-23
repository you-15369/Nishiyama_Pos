/** UT-FE-04 金額表示 */
import { isValidProductCode, taxLabel, yen } from "@/lib/format";

describe("金額の表示", () => {
  it("合計の表示", () => {
    expect(yen(1189)).toBe("¥1,189");
    expect(yen(1234567)).toBe("¥1,234,567");
    expect(yen(0)).toBe("¥0");
    expect(yen(-59)).toBe("−¥59");
  });
  it("税率の表示はサーバの適用税率を使う", () => {
    expect(taxLabel("reduced", 0.08)).toBe("税8%");
    expect(taxLabel("standard", 0.1)).toBe("税10%");
    expect(taxLabel("reduced")).toBe("軽減税率");
  });
  it("商品コードは数字13桁", () => {
    expect(isValidProductCode("4901234567894")).toBe(true);
    expect(isValidProductCode("490123456789")).toBe(false);
    expect(isValidProductCode("49012345678AB")).toBe(false);
  });
});
