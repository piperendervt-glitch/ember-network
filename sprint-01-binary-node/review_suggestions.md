# Review Suggestions: Sprint 1 改善案 (コード差分)

Self Review の「改善優先度トップ 5」について具体的な diff を提示する。
**実装はまだ変更していない**。Robosheep の判断後に実施する。

行番号は現在の commit (未 commit) 状態の行番号。

---

## 改善案 1: `update()` の bool 拒否

### 変更前のコード

`src/binary_node.py` L60-87:

```python
60  def update(self, input_value: int) -> None:
61      """
62      1 ステップの更新。
63
64      Parameters
65      ----------
66      input_value : int
67          0 または 1。
68
69      Raises
70      ------
71      ValueError
72          input_value が 0 または 1 以外の場合。
73      """
74      if input_value not in (0, 1):
75          raise ValueError(
76              f"input_value must be 0 or 1, got {input_value!r}"
77          )
78      new_weight = (
79          self._weight
80          + self._learning_rate * input_value
81          - self._forgetting_rate
82      )
83      if new_weight < 0.0:
84          new_weight = 0.0
85      elif new_weight > 1.0:
86          new_weight = 1.0
87      self._weight = new_weight
```

### 変更後のコード

```python
def update(self, input_value: int) -> None:
    """
    1 ステップの更新。

    Parameters
    ----------
    input_value : int
        0 または 1。bool 型は明示的に拒否する。

    Raises
    ------
    ValueError
        input_value が 0 または 1 (int) でない場合、または bool 型の場合。
    """
    if isinstance(input_value, bool) or input_value not in (0, 1):
        raise ValueError(
            f"input_value must be 0 or 1 (int, not bool), "
            f"got {input_value!r} of type {type(input_value).__name__}"
        )
    new_weight = (
        self._weight
        + self._learning_rate * input_value
        - self._forgetting_rate
    )
    if new_weight < 0.0:
        new_weight = 0.0
    elif new_weight > 1.0:
        new_weight = 1.0
    self._weight = new_weight
```

### テストの差分

`tests/test_basic.py` L75-80:

**変更前:**
```python
def test_invalid_input_raises_value_error():
    """input_value が 0 または 1 以外の場合 ValueError が発生する。"""
    node = BinaryNode()
    for invalid in (-1, 2, 0.5, 100):
        with pytest.raises(ValueError):
            node.update(invalid)
```

**変更後:**
```python
def test_invalid_input_raises_value_error():
    """input_value が 0 または 1 (int) 以外の場合 ValueError が発生する。

    bool 型 (True, False) も明示的に拒否する。Python では bool が int の
    サブクラスのため `True in (0, 1)` は True を返す。これは仕様上の
    曖昧さを排除するため拒否する。
    """
    node = BinaryNode()
    for invalid in (-1, 2, 0.5, 100, True, False, None, "1"):
        with pytest.raises(ValueError):
            node.update(invalid)
```

注: `None`, `"1"` も追加したが、`None not in (0, 1)` および
`"1" not in (0, 1)` はどちらも True なので、現実装でも ValueError になる。
追加検証として残す。

### 修正の根拠

- Python の bool は int のサブクラスで、`True == 1`, `False == 0`
- 現実装は bool を意図せず受け入れる (サイレント許容)
- 仕様書「input_value: int で 0 または 1」を厳格に解釈すると bool は拒否すべき
- Sprint 2 で input が連続値に拡張される際、型ガードの基準を明確化する

### 修正による副作用の可能性

- `isinstance(input_value, bool)` の追加チェックは O(1) で性能影響なし
- 既存テストへの影響: なし (現テストは bool を渡していない)
- visualize.py への影響: なし (整数 0/1 を直接渡している)
- 想定外影響: もし Sprint 2 以降で bool を意図的に input として使う設計に
  なった場合、この validation を緩める必要がある

### テストへの影響

- 既存 9 テストはすべて影響なし (継続 pass)
- `test_invalid_input_raises_value_error` の検証ケースが 4 → 8 に増加
- 新規テストファイルは不要

---

## 改善案 2: `test_reproducibility.py` を意味あるテストに書き換え

### 変更前のコード

`tests/test_reproducibility.py` 全体を確認。
- L51-58: `test_constant_input_bit_perfect_across_seeds` (現状維持予定)
- L61-68: `test_cessation_bit_perfect_across_seeds` (現状維持予定)
- L71-75: `test_same_seed_produces_same_result` (現状維持予定)

### 変更後のコード (追加)

`tests/test_reproducibility.py` の末尾に追加:

```python
def test_model_is_seed_independent():
    """現モデルは決定論的でシードに依存しないことを明示確認。

    BinaryNode が random/numpy のグローバル状態を消費していない場合、
    シード設定なしの実行と、シード設定ありの実行で結果が完全一致するはず。

    このテストの意図:
    - Sprint 1 では現モデル (シード非依存) の決定論性を明示証拠化
    - Sprint 2 以降で確率要素を導入した場合、このテストは fail するはず
      → 「意図した変化の検出器」として機能する

    注意:
    - 他のテストでグローバルシードが既に設定されている可能性があるため、
      本テストでは状態を意識的に呼び出し順で検証する。
    """
    # シード設定なしで 100 ステップ
    node1 = BinaryNode()
    traj1 = [node1.weight]
    for _ in range(100):
        node1.update(1)
        traj1.append(node1.weight)

    # シード設定ありで 100 ステップ (異なるシード値で 2 回)
    random.seed(42)
    np.random.seed(42)
    node2 = BinaryNode()
    traj2 = [node2.weight]
    for _ in range(100):
        node2.update(1)
        traj2.append(node2.weight)

    random.seed(12345)
    np.random.seed(12345)
    node3 = BinaryNode()
    traj3 = [node3.weight]
    for _ in range(100):
        node3.update(1)
        traj3.append(node3.weight)

    # 全 3 軌跡が完全一致 = シードに依存しないことの証明
    assert np.array_equal(np.array(traj1), np.array(traj2))
    assert np.array_equal(np.array(traj1), np.array(traj3))
```

### 既存テストの docstring 更新

`tests/test_reproducibility.py` の冒頭 docstring を更新:

**変更前 (L1-10):**
```python
"""
test_reproducibility: KR-S3 の検証

5 つの異なるランダムシードで完全に同じ結果が再現されることを確認する。
現在のモデルは決定論的なので、シードに依存しない (シードを設定しても
出力に影響しない) ことが期待される。

シード設定は random.seed() と np.random.seed() の両方を呼ぶことで、
将来的に確率的要素を導入した際の一貫性も担保する。
"""
```

**変更後:**
```python
"""
test_reproducibility: KR-S3 の検証

5 つの異なるランダムシードで完全に同じ結果が再現されることを確認する。
現在のモデルは決定論的なので、本来シードに依存しない。

このテストファイルは 2 つの目的を持つ:

1. KR-S3 文言の達成証拠 (test_*_bit_perfect_across_seeds, test_same_seed_*)
   - 5 シードで同一結果が出ることを bit-perfect に確認

2. 現モデルのシード非依存性の明示証明 (test_model_is_seed_independent)
   - シード設定なしの結果とシード設定ありの結果が一致することで、
     BinaryNode が random/numpy のグローバル状態を消費していないことを示す
   - Sprint 6-7 で確率要素 (個体差) を導入した場合、このテストは
     fail するはず → 意図した変化の検出器として機能する

シード設定は random.seed() と np.random.seed() の両方を呼ぶことで、
将来的に確率的要素を導入した際の一貫性インフラを Sprint 1 から確立する。
"""
```

### 修正の根拠

- 現テスト群は「シードを設定して計算するが、計算がシード非依存」という
  状態を「再現性」と解釈しており、KR-S3 の意図 (再現性インフラの確立) を
  間接的にしか反映していない
- 新規テスト `test_model_is_seed_independent` は明示的に「現モデルが
  シードに依存しない」ことを検証 → Sprint 2 以降で意図せずシード依存に
  なった場合の早期検出器として機能

### 修正による副作用の可能性

- 新規テストはグローバルシードを変更する副作用がある
  - test_*_bit_perfect_across_seeds も同様の副作用を持つので、現状で既に
    テスト間の順序依存性が潜在
  - pytest はデフォルトで定義順に実行するが、保証はない
  - 厳密にはテストごとに `random.getstate()` / `np.random.get_state()` で
    保存・復元すべきだが、現 Sprint では Out of Scope と判断
- 既存テストへの影響: なし

### テストへの影響

- 新規テスト 1 件追加 (合計 24 件)
- 既存 3 テストはそのまま継続 pass
- docstring 更新でテストの意図が明確化

---

## 改善案 3: `test_clipping_activates_at_t21` を真の clip 検証に置換

### 変更前のコード

`tests/test_constant_input.py` L51-58:

```python
51  def test_clipping_activates_at_t21():
52      """t=21 で実際に clip 機能が発動 (1.0 + 0.05 → 1.0 に切り詰め)。
53
54      t=20 では (1.0 - ε) であり厳密には clip 不要、t=21 で初めて
55      weight + 0.05 > 1.0 となり clip が発動する。
56      """
57      trajectory = _run_constant_input(100)
58      assert trajectory[21] == 1.0
```

### 変更後のコード

```python
def test_clipping_prevents_upper_overflow():
    """weight が 1.0 に到達後、追加 input でも 1.0 を超えないこと。

    検証ロジック:
    - 20 ステップ input=1 で weight ≒ 1.0 (誤差 < 1e-10) に到達
    - さらに 1 ステップ input=1 を与えると、clip がなければ
      weight + 0.05 → ~1.05 になるはず
    - 実測 weight が厳密に 1.0 であることで、clip 機能の発動を確認

    このテストは clip ロジックを直接検証するため、もし将来 clip を
    意図せず削除した場合、本テストは fail する (regression detection)。
    """
    node = BinaryNode()
    for _ in range(20):
        node.update(1)

    # この時点で weight ≒ 1.0
    pre_clip_weight = node.weight
    assert abs(pre_clip_weight - 1.0) < 1e-10, (
        f"前提条件: 20 ステップ後の weight が 1.0 近傍であること。"
        f"実測 = {pre_clip_weight}"
    )

    # clip がなければ weight = pre_clip + 0.05 ≒ 1.05 になるはず
    naive_next = pre_clip_weight + 0.05
    assert naive_next > 1.0, (
        f"clip テストの前提: clip がない場合に 1.0 を超えるはず。"
        f"naive_next = {naive_next}"
    )

    # 実際に update を呼び、clip が発動して 1.0 にスナップされることを確認
    node.update(1)
    assert node.weight == 1.0, (
        f"clip 発動後の weight は厳密に 1.0 になるべき。実測 = {node.weight}"
    )
```

### 修正の根拠

- 旧テストは「t=21 で weight==1.0」のみ検証 → clip 機能が壊れていなくても
  weight が偶然 1.0 になる実装に変更されると pass してしまう
- 新テストは:
  1. 「clip 直前の weight」を取得
  2. 「clip がなければ weight + 0.05 > 1.0」を assert (テストの前提条件確認)
  3. 「update 後 weight == 1.0」を assert (clip 発動の証拠)
- これにより clip ロジックが直接検証される

### 修正による副作用の可能性

- テスト名が `test_clipping_activates_at_t21` → `test_clipping_prevents_upper_overflow`
  に変わるため、CI 履歴での比較ができなくなる (新規テスト扱いになる)
- 旧テストでカバーされていた「t=21 で weight==1.0」の確認は、
  `test_weight_is_stable_at_one_from_t20_to_t100` (t=20-100 を全 check) で
  既にカバーされているため、削除しても regression は発生しない
- 0 側の clip (下限) の対称テストもあるべきかは別問題 (項目 5 で言及)

### テストへの影響

- `test_clipping_activates_at_t21` を `test_clipping_prevents_upper_overflow`
  に置換 (テスト数は変わらず 5 件)
- 関連で下限 clip のテストも追加する場合は別途 (本案には含めない)

---

## 改善案 4: `plot_reproducibility.png` に max(|diff|) アノテーション追加

### 変更前のコード

`visualize.py` L170-206:

```python
170  def plot_reproducibility() -> Path:
171      """KR-S3 のプロットを生成 (5 シードでの完全一致を視覚化)。"""
172      trajectories = {seed: run_with_seed(seed) for seed in SEEDS}
173      t = np.arange(TOTAL_STEPS + 1)
174
175      fig, ax = plt.subplots(figsize=(8, 5))
176      linestyles = ["-", "--", "-.", ":", (0, (5, 10))]
177      colors = ["blue", "orange", "green", "red", "purple"]
178      for (seed, traj), ls, col in zip(
179          trajectories.items(), linestyles, colors
180      ):
181          ax.plot(
182              t,
183              traj,
184              color=col,
185              linestyle=ls,
186              linewidth=1.5,
187              label=f"seed={seed}",
188              alpha=0.7,
189          )
190
191      ax.set_xlabel("time step")
192      ax.set_ylabel("weight")
193      ax.set_title(
194          "KR-S3: Reproducibility across 5 seeds "
195          "(deterministic model: lines overlap)"
196      )
197      ax.set_xlim(0, TOTAL_STEPS)
198      ax.set_ylim(-0.05, 1.1)
199      ax.legend(loc="lower right")
200      ax.grid(True, alpha=0.3)
201
202      out_path = PLOTS_DIR / "plot_reproducibility.png"
203      fig.tight_layout()
204      fig.savefig(out_path, dpi=120)
205      plt.close(fig)
206      return out_path
```

### 変更後のコード

```python
def plot_reproducibility() -> Path:
    """KR-S3 のプロットを生成 (5 シードでの完全一致を視覚化)。

    視覚的な「重なり」だけでは判別困難なため、5 軌跡間の最大絶対差分
    `max(|diff|)` をプロット内テキストとして表示し、bit-perfect 一致を
    数値証拠として示す。
    """
    trajectories = {seed: run_with_seed(seed) for seed in SEEDS}
    t = np.arange(TOTAL_STEPS + 1)

    # 数値証拠: 5 軌跡間の最大絶対差分を計算
    reference = trajectories[SEEDS[0]]
    max_diff = max(
        float(np.max(np.abs(traj - reference)))
        for traj in trajectories.values()
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    linestyles = ["-", "--", "-.", ":", (0, (5, 10))]
    colors = ["blue", "orange", "green", "red", "purple"]
    for (seed, traj), ls, col in zip(
        trajectories.items(), linestyles, colors
    ):
        ax.plot(
            t,
            traj,
            color=col,
            linestyle=ls,
            linewidth=1.5,
            label=f"seed={seed}",
            alpha=0.7,
        )

    # 数値証拠をプロット内に表示
    ax.text(
        0.05, 0.95,
        f"Numerical evidence:\nmax(|diff|) across 5 seeds = {max_diff:.2e}",
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(
            boxstyle="round",
            facecolor="white",
            edgecolor="gray",
            alpha=0.9,
        ),
    )

    ax.set_xlabel("time step")
    ax.set_ylabel("weight")
    ax.set_title(
        "KR-S3: Reproducibility across 5 seeds "
        "(deterministic model: lines overlap)"
    )
    ax.set_xlim(0, TOTAL_STEPS)
    ax.set_ylim(-0.05, 1.1)
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)

    out_path = PLOTS_DIR / "plot_reproducibility.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path
```

### 修正の根拠

- 5 シードでの bit-perfect 一致を視覚的に示すだけでは「見た目で重なって
  いる」と「実際に同一」が区別困難
- `max(|diff|) = 0.00e+00` を数値で示すことで、CLAUDE.md Rule 3
  (結果の証拠化) を視覚プロットでも満たす
- 論文公開時 (Mission KR-M1) のプロット品質基準として、Sprint 1 から
  「数値証拠の埋め込み」習慣を確立

### 修正による副作用の可能性

- プロットの左上に注釈ボックスが配置されるため、データの一部が
  視覚的に隠れる可能性
  - 現データは t=0 で weight=0 から始まるため、左上の領域 (t=0-20, weight=0.5-1.1)
    にはデータがない → 影響なし
- max_diff の計算は O(N) で性能影響は無視できる

### テストへの影響

- visualize.py のテストは存在しない (Sprint 1 では visualize は手動確認)
- 影響なし

---

## 改善案 5: `Examples` doctest の自動実行を有効化

### 変更前の状態

- `src/binary_node.py` の `Examples` セクション (L44-51):
  ```python
  Examples
  --------
  >>> node = BinaryNode()
  >>> node.weight
  0.0
  >>> node.update(1)
  >>> round(node.weight, 10)
  0.05
  ```
- `pytest tests/` で実行されるが、`--doctest-modules` フラグが未設定のため
  doctest は実行されない

### 変更後のコード (新規ファイル作成)

`pytest.ini` を新規作成:

```ini
[pytest]
addopts = --doctest-modules --doctest-glob=*.py
testpaths = src tests
```

または、`pyproject.toml` ではなく軽量な `pytest.ini` を推奨。

### 副作用の検証 (実装前の確認)

`--doctest-modules` を有効化すると:
- `src/binary_node.py` の Examples が doctest として実行される ✓
- `tests/*.py` も doctest 対象に含まれる
  - 各テストファイルのトップ docstring に `>>>` がない限り、影響なし
  - 現状の test_*.py は doctest 形式の例を含まないため安全
- `visualize.py` も対象外 (testpaths に含まれていない)
  - ただし testpaths に visualize.py を追加した場合は要注意

### 別案: pytest.ini を作らず、既存テストに doctest 呼び出しを追加

```python
# tests/test_basic.py の末尾に追加
def test_docstring_examples():
    """src/binary_node.py の Examples セクションを doctest として実行。"""
    import doctest
    import binary_node
    results = doctest.testmod(binary_node, verbose=False)
    assert results.failed == 0, f"doctest failures: {results.failed}"
```

この別案は pytest.ini 不要で、影響範囲が局所化される。
**こちらを推奨**。

### 修正の根拠

- docstring に書いた Examples は「実行されないテキスト」となっており、
  「動かないテスト」(self review で指摘) と同じ問題
- doctest を実行することで、API の使用例が常に最新仕様と整合することを
  保証
- Sphinx + napoleon でドキュメント生成する際の品質保証にも寄与

### 修正による副作用の可能性

- 別案 (test_docstring_examples を追加) の場合:
  - 副作用なし (既存テストへの影響ゼロ)
  - 1 件のテスト追加のみ
- pytest.ini 案の場合:
  - testpaths や addopts の設定が CI 設定や IDE 設定と競合する可能性
  - Sprint 2 以降で他のオプションを追加したくなった時の柔軟性が下がる

### テストへの影響

- 別案推奨: `test_basic.py` に `test_docstring_examples` 1 件追加 (合計 10 件)
- pytest.ini 案: 既存テストに影響なし、doctest が追加で実行される

---

## 全変更サマリ

| # | 変更ファイル | 変更行数概算 | 新規テスト数 |
|---|------------|------------|------------|
| 1 | `src/binary_node.py` (L73-77), `tests/test_basic.py` (L75-80) | +5/-3 | 0 件 (既存拡張) |
| 2 | `tests/test_reproducibility.py` (末尾追加 + docstring 更新) | +35 | +1 件 |
| 3 | `tests/test_constant_input.py` (L51-58 置換) | +20/-7 | 0 件 (置換) |
| 4 | `visualize.py` (L170-206 拡張) | +15 | 0 件 |
| 5 | `tests/test_basic.py` (末尾追加、別案) | +6 | +1 件 |

**合計: テスト数 23 → 24 件 (新規 +1)**

実装後、`pytest tests/ -v` および `python visualize.py` を再実行し、
全テスト pass + 3 プロット生成 + 数値証拠表示を確認する。

承認後、各項目を Robosheep 指示の順序で実施する。

---

## 注記: 改善案 5 (doctest) の Sprint 2 への予約

本ドキュメントの上記表は **5 つの改善案を全て実施した場合** のテスト数
変化を示している。

しかし、Sprint 1 で実施されたのは `critical_review_points.md` の 5 項目
(項目 5 = `ai_metrics/sprint-01_ai_log.md` 作成) であり、
本ドキュメント改善案 5 (doctest 実行有効化) は **Sprint 1 の修正範囲外**
となった。

そのため:

- Sprint 1 の実測テスト数変化: **23 → 24 件 (+1)**
  (改善案 1, 2, 3, 4 のうち、新規テスト追加は改善案 2 のみ)
- 改善案 5 (doctest 実行有効化) は **Sprint 2 の最初の Backlog 項目として予約**
- 詳細は `deferred_issues.md` の「Sprint 2 で最初に対応する項目」セクションを参照

この扱いにより、Sprint 1 の境界を明確に保ちつつ、doctest 改善の価値も
Sprint 2 で確実に確保する。
