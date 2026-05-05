# Sprint 4 Mutation Testing Summary (Task 16, KR-S8)

## 実行環境

- ツール: mutmut 3.5.0
- 実行環境: WSL Ubuntu 24.04 LTS, Python 3.12.3
- 実行ディレクトリ: `~/sprint-04-mutmut/` (Linux ファイルシステム上のコピー)
  - 理由: mutmut が `mutants/` ディレクトリ生成時に /mnt/c (Windows 側) で
    permission エラーを起こすため
- 実行コマンド: `python -m mutmut run --max-children 2`
- 並列度: 2 worker
- 実行時間: 約 3 分 20 秒 (1.89 mutations/second)

## kill rate サマリ

| 区分 | 件数 | 割合 |
|------|------|------|
| 総 mutant 数 | 381 | 100.00% |
| 🎉 killed | 304 | 79.79% |
| 🙁 survived | 76 | 19.95% |
| ⏰ timeout | 1 | 0.26% |
| 🤔 suspicious | 0 | 0.00% |
| 🫥 no test | 0 | 0.00% |
| 🔇 skipped | 0 | 0.00% |
| 🧙 magic | 0 | 0.00% |

**kill rate = 304 / 381 = 79.79%**

Sprint 4 Tripwire #8 (kill rate < 50%) は **発動せず**。

## ファイル別 mutant 分布

mutmut が変異対象とした関数の数:

- `src/temperature_node.py`: 10 関数
- `src/analytical.py`: 4 関数
- `src/mms.py`: 12 関数
- `src/__init__.py`: 1 ファイル無視 (do_not_mutate 設定)

## 環境構築の障害ログ

mutmut を Sprint 4 環境で動作させるため、以下の対処を実施 (PRL-015 として記録):

1. **Windows 非対応**: `python -m mutmut` は Windows で「please use the WSL」
   メッセージを表示。WSL Ubuntu 24.04 LTS をインストール。
2. **`/mnt/c` 上で venv 作成不可**: `Operation not permitted` エラー。
   venv を `~/venv-sprint4-wsl/` (Linux fs) に作成して回避。
3. **`/mnt/c` 上で `mutants/` ディレクトリ生成不可**: ソースを
   `~/sprint-04-mutmut/` に複製して回避。
4. **`scenarios.py` が `tests_dir` 外にある**: テストが
   `from scenarios import ...` するため、`setup.cfg` に
   `also_copy = scenarios.py` を追加。
5. **Sprint 3 比較テストの相対パス**: `_SPRINT4.parent / "sprint-03-temperature"`
   が `mutants/` 経由だと存在しない場所を指す。`~/sprint-04-mutmut/sprint-03-temperature`
   に Sprint 3 への symlink を追加して解決。
6. **`multiprocessing.set_start_method('fork')` の重複呼び出し**: trampoline
   が `mutmut.__main__` を import する際に再実行され `RuntimeError: context
   has already been set`。`tests/conftest.py` で `MUTANT_UNDER_TEST` 環境
   変数があるとき `set_start_method` を tolerant 版に monkey-patch して回避。

## 生存 mutant のカテゴリ分析

76 件の生存 mutant を、原因別に分類:

### カテゴリ A: デフォルト引数値の変異 (約 8 件)

例: `analytical.x_analytical_temperature__mutmut_1`
- `heating_rate: float = 0.1` → `heating_rate: float = 1.1`

すべての test がパラメータを明示的に渡すため、デフォルト値の変異は検出
されない。これは equivalent mutant の典型例。

### カテゴリ B: エラーメッセージ文字列の変異 (約 12 件)

例: `temperature_node.xǁTemperatureNodeǁupdate__mutmut_3`
- `f"input_value must be a number in [0, 1], got ..."` → `None`

ValueError は raise されるが、test は exception type のみ assert し、
メッセージ内容は assert していないため検出されない。

### カテゴリ C: 境界条件 `<` ⇄ `<=` の変異 (約 5 件)

例: `temperature_node.xǁTemperatureNodeǁupdate__mutmut_69`
- `if new_T < self._T_env:` → `if new_T <= self._T_env:`

new_T == T_env の境界点でしか挙動が変わらず、テストが境界値ちょうど
に到達するケースを検証していない。

### カテゴリ D: T_ref ≠ 0 / T_env ≠ 0 の coverage gap (3 件)

例: `analytical.x_analytical_temperature__mutmut_18`
- `a = h·u·(1 - α·T_ref) + c·T_env` → `a = h·u·(1 - α·T_ref) - c·T_env`

すべての test が `T_env = 0.0` (および T_ref = T_env = 0) を使用する
ため、`cooling_rate * T_env = 0` となり mutation の影響が現れない。
**これは真の coverage gap** (Sprint 4 で T_env > 0 シナリオを検証
していない)。

### カテゴリ E: dt の特定値による分岐 (1 件)

`temperature_node.xǁTemperatureNodeǁupdate__mutmut_15`
- `if dt == 0:` → `if dt == 1:`

mutated コードでは dt=1 で no-op (積分しない)。テストで使用される
dt は 0.01, 0.1, 0.05 など 1.0 以外なので、original も mutated も
no-op に入らない。dt=0 の case ではどちらも `T = T + 0 * (...)` なので
区別できない。**これも coverage gap** (dt=1 を使う test が存在しない)。

### カテゴリ F: MMS 内部の冗長変異 (約 25 件)

`src/mms.py` 内の `manufactured_polynomial`, `manufactured_trigonometric`
等の係数変更。MMS は KR-S7 で「製造解と数値解の誤差 < 1e-6」を検証する
が、製造解の関数定義そのものを変えても、source term と一貫していれば
検出されない (これは MMS 手法の本質的限界)。

### カテゴリ G: timeout (1 件)

`temperature_node.xǁTemperatureNodeǁ__init____mutmut_6`
mutmut が指定時間内に test を完了できなかった。原因不明 (おそらく
無限ループ系の変異)。

## α_PTC = 0.5 (critical curve) 関連の物理的観察

**重要な発見**: ソースコードに `0.5` という定数は**直接出現しない**。

α_PTC = 0.5 は閾値定数ではなく、`b = α_PTC · heating_rate · input - cooling_rate`
の係数バランスから創発する物理量である:

- `heating_rate = 0.1`, `cooling_rate = 0.05` のとき
- `b = 0` ⇔ `α_PTC · input = 0.5`
- `α_PTC = 0.5, input = 1.0` または `α_PTC = 1.0, input = 0.5` 等

そのため、α_PTC = 0.5 を直接 mutate する mutation は存在しない。
代わりに、b = 0 分岐 (`if b == 0:` の判定) と b の係数を構成する
要素 (heating_rate, cooling_rate, alpha_PTC, input_value) の各係数
が独立に mutate される。

これらのうち、test が定数を明示的に渡しているもの (heating_rate, cooling_rate)
は default 値変異が survived し、test が走査しているもの (alpha_PTC を
KR-S2 で 5 値スイープ) は killed されている。

つまり、Sprint 4 の test は **「α_PTC を変えたとき」** には敏感だが、
**「heating_rate や cooling_rate のバランスが変わったとき」** には
鈍感である。これは KR-S2 が α_PTC スイープに特化していることの
裏返しでもあり、設計上の意図と整合している。

## Sprint 5 以降への提言

1. T_env > 0 (例: T_env = 5.0) でのシナリオを 1-2 件追加すれば、
   カテゴリ D の 3 件の survived mutant を kill できる (kill rate
   が 81% 程度に上昇)。
2. dt = 1.0 を含む test を追加すれば、カテゴリ E の 1 件を kill できる。
3. heating_rate / cooling_rate のスイープ test を 1 件追加すれば、
   default 値変異 (カテゴリ A) のうち数件が kill できる。

ただし、これらは Sprint 4 の Out of Scope 範囲であるため、Sprint 5
以降の議題とする。

## 詳細結果

完全な survived/timeout mutant リストは `mutmut_results.txt` を参照。
