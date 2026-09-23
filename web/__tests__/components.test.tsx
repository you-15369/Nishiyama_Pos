/** UT-FE-05〜08 */
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ManualCodeInput from "@/components/ManualCodeInput";
import MemberInput from "@/components/MemberInput";
import PosScreen from "@/components/PosScreen";
import Scanner, { type StartScan } from "@/components/Scanner";
import { ApiError, type ApiClient } from "@/lib/apiClient";
import type { Quote } from "@/lib/types";

jest.mock("next/navigation", () => ({ useRouter: () => ({ replace: jest.fn(), push: jest.fn() }) }));

describe("ManualCodeInput", () => {
  it("不正な商品コードは追加不可", async () => {
    const onAdd = jest.fn().mockResolvedValue(true);
    render(<ManualCodeInput onAdd={onAdd} />);
    const button = screen.getByRole("button", { name: "追加" });
    expect(button).toBeDisabled(); // 空
    await userEvent.type(screen.getByLabelText(/商品コード/), "49012abc");
    expect(button).toBeDisabled(); // 非数字
    expect(screen.getByText("数字13桁で入力してください")).toBeInTheDocument();
    await userEvent.clear(screen.getByLabelText(/商品コード/));
    await userEvent.type(screen.getByLabelText(/商品コード/), "4901234567894{Enter}");
    expect(onAdd).toHaveBeenCalledWith("4901234567894");
  });
});

describe("Scanner", () => {
  it("検知したコードをonScanに渡す", async () => {
    let emit: (t: string) => void = () => {};
    const startScan: StartScan = async (_video, onText) => {
      emit = onText;
      return { stop: jest.fn() };
    };
    const onScan = jest.fn();
    render(<Scanner onScan={onScan} startScan={startScan} />);
    await userEvent.click(screen.getByRole("button", { name: "カメラを起動" }));
    await screen.findByText("カメラ起動中");
    act(() => emit("4901234567894"));
    expect(onScan).toHaveBeenCalledWith("4901234567894");
    act(() => emit("4901234567894")); // 直後の同じコードは重複として無視
    expect(onScan).toHaveBeenCalledTimes(1);
  });

  it("カメラが使えないときは手入力を案内する", async () => {
    const startScan: StartScan = async () => {
      throw new Error("NotAllowedError");
    };
    render(<Scanner onScan={jest.fn()} startScan={startScan} />);
    await userEvent.click(screen.getByRole("button", { name: "カメラを起動" }));
    expect(await screen.findByText(/カメラを使えません/)).toBeInTheDocument();
  });
});

describe("MemberInput", () => {
  it("会員IDを読み込むとonLoadが呼ばれる", async () => {
    const onLoad = jest.fn();
    const { rerender } = render(<MemberInput memberId={null} memberName={null} onLoad={onLoad} onClear={jest.fn()} />);
    expect(screen.getByText("会員なし")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("会員カード"), "M0001");
    await userEvent.click(screen.getByRole("button", { name: "読込" }));
    expect(onLoad).toHaveBeenCalledWith("M0001");
    rerender(<MemberInput memberId="M0001" memberName="テスト太郎" onLoad={onLoad} onClear={jest.fn()} />);
    expect(screen.getByText("テスト太郎 様")).toBeInTheDocument();
  });
});

describe("PosScreen", () => {
  const quote = (unit: number): Quote => ({
    member_id: null,
    lines: [{ product_code: "4901234567894", name: "おにぎり 鮭", unit_price: unit, quantity: 1, discount_amount: 0, tax_class: "reduced", applied_rate: 0.08, subtotal: unit }],
    total_ex_tax: unit,
    total_discount: 0,
    taxable_by_class: { reduced: unit, standard: 0 },
    tax_by_class: { reduced: Math.floor(unit * 0.08), standard: 0 },
    total_in_tax: unit + Math.floor(unit * 0.08),
  });

  function makeApi(overrides: Partial<ApiClient> = {}): ApiClient {
    return {
      login: jest.fn(),
      logout: jest.fn(),
      me: jest.fn().mockResolvedValue({ staff_id: 1, login_id: "S001", name: "山田 太郎" }),
      taxRates: jest.fn().mockResolvedValue([{ tax_class: "reduced", rate: 0.08 }, { tax_class: "standard", rate: 0.1 }]),
      getMember: jest.fn(),
      getProduct: jest.fn().mockResolvedValue({ product_code: "4901234567894", name: "おにぎり 鮭", unit_price: 150, tax_class: "reduced" }),
      price: jest.fn().mockResolvedValue(quote(150)),
      purchase: jest.fn(),
      ...overrides,
    } as ApiClient;
  }

  async function addOnigiri() {
    await userEvent.type(screen.getByLabelText(/商品コード/), "4901234567894{Enter}");
    await waitFor(() => expect(screen.getByTestId("total-in-tax")).toHaveTextContent("¥162"));
  }

  it("金額不一致時はサーバ値で同期", async () => {
    const serverQuote = quote(160);
    const api = makeApi({
      purchase: jest.fn().mockRejectedValue(new ApiError(422, "TOTAL_MISMATCH", "金額を更新しました", serverQuote)),
    });
    render(<PosScreen api={api} />);
    await addOnigiri();
    (api.price as jest.Mock).mockResolvedValue(serverQuote);
    await userEvent.click(screen.getByRole("button", { name: "購入する" }));
    await waitFor(() => expect(screen.getByTestId("total-in-tax")).toHaveTextContent("¥172"));
    expect(screen.getByText(/金額を更新しました/)).toBeInTheDocument();
    expect(api.purchase).toHaveBeenCalledWith(null, [{ product_code: "4901234567894", quantity: 1 }], 162);
  });

  it("購入後は登録欄と購入リストが空になる", async () => {
    const api = makeApi({
      purchase: jest.fn().mockResolvedValue({ transaction_id: 7, total_ex_tax: 150, total_discount: 0, total_in_tax: 162, tax_by_class: { reduced: 12, standard: 0 }, transacted_at: "" }),
    });
    render(<PosScreen api={api} />);
    await addOnigiri();
    await userEvent.click(screen.getByRole("button", { name: "購入する" }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("¥162");
    await userEvent.click(screen.getByRole("button", { name: "次の会計へ" }));
    expect(screen.getByText(/商品をスキャンするか/)).toBeInTheDocument();
    expect(screen.getByTestId("total-in-tax")).toHaveTextContent("¥0");
  });

  it("未登録商品はリストに追加しない", async () => {
    const api = makeApi({ getProduct: jest.fn().mockRejectedValue(new ApiError(404, "PRODUCT_NOT_FOUND", "商品がマスタ未登録です")) });
    render(<PosScreen api={api} />);
    await userEvent.type(screen.getByLabelText(/商品コード/), "4999999999999{Enter}");
    expect(await screen.findByText(/商品がマスタ未登録です/)).toBeInTheDocument();
    expect(screen.getByText(/0品目/)).toBeInTheDocument();
  });
});

describe("存在しない会員ID", () => {
  it("読み込めず、入力欄は残り、会員なしのまま", async () => {
    const onLoad = jest.fn().mockResolvedValue(false);
    render(<MemberInput memberId={null} memberName={null} onLoad={onLoad} onClear={jest.fn()} />);
    await userEvent.type(screen.getByLabelText("会員カード"), "M9999");
    await userEvent.click(screen.getByRole("button", { name: "読込" }));
    expect(onLoad).toHaveBeenCalledWith("M9999");
    expect(screen.getByLabelText("会員カード")).toHaveValue("M9999");
    expect(screen.getByText("会員なし")).toBeInTheDocument();
  });

  it("レジ画面でエラーを表示し、会員として扱わない", async () => {
    const api = {
      login: jest.fn(),
      logout: jest.fn(),
      me: jest.fn().mockResolvedValue({ staff_id: 1, login_id: "S001", name: "山田 太郎" }),
      taxRates: jest.fn().mockResolvedValue([]),
      getMember: jest.fn().mockRejectedValue(new ApiError(404, "MEMBER_NOT_FOUND", "会員が見つかりません")),
      getProduct: jest.fn(),
      price: jest.fn(),
      purchase: jest.fn(),
    } as unknown as ApiClient;
    render(<PosScreen api={api} />);
    await userEvent.type(screen.getByLabelText("会員カード"), "M9999{Enter}");
    expect(await screen.findByText(/会員が見つかりません（M9999）/)).toBeInTheDocument();
    expect(screen.getByText("会員なし")).toBeInTheDocument();
  });
});
