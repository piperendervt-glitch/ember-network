# Sprint 2 OKR: continuous time and time constants

ember-network シミュレーション開発 Phase の 2 つ目の Sprint。
AAS 核心ルールを連続時間の微分方程式として実装し、解析解との一致と
数値積分手法の収束性を検証する。

## Sprint Objective

AAS 核心ルールを連続時間の微分方程式として実装し、解析解との一致と
数値積分手法の収束性を検証する

## 数学モデル

```
dw/dt = α·input(t) - β·w(t)
```

| 記号 | 値 | 意味 |
|------|-----|------|
| α | 0.1 | 学習率 (加熱強度に相当) |
| β | 0.05 | 忘却率 (冷却強度に相当) |
| w_eq = α/β | 2.0 | clip なし平衡点 |
| τ = 1/β | 20.0 | 時定数 |
| t_clip = 20·ln(2) | 13.8629... | clip なし解が w=1.0 到達する時刻 |

### Sprint 1 との違い

forgetting term が `-β` (定数) から `-β·w(t)` (weight 比例) に変更される。
理由: Newton 冷却則と同型 (物理的妥当性)、解析解 (指数関数) が存在、
時定数の概念が明確化、Sprint 3 以降の温度変数導入への自然な接続。

### 解析解 (clip なし)

```
input=1: w(t) = w_eq + (w_0 - w_eq) · exp(-β·t)  where w_eq = α/β
input=0: w(t) = w_0 · exp(-β·t)
```

## Sprint Key Results

### KR-S1: clip なし実装、入力ありでの解析解との一致

clip なし実装で input=1 を一定に与えた場合、数値解と解析解が高精度で一致。

達成判定:
- input=1 を 100 単位時間与え、初期値 w_0=0
- 数値解 (RK4, dt=0.01) と解析解の最大誤差: `max(|w_num(t) - w_ana(t)|) < 1e-6`
- 全 t in [0, 100] で成立

### KR-S2: clip なし実装、入力停止後の解析解との一致

clip なし実装で、まず input=1 で w が高い値に到達した後、input=0 に切替。

達成判定:
- t=0 から t=50 まで input=1、t=50 から t=100 まで input=0
- 数値解 (RK4, dt=0.01) と解析解の最大誤差 < 1e-6

### KR-S3: clip 付き実装で Sprint 1 と類似の挙動

clip 付き実装で clip による頭打ちを確認し、解析的予測との一致を検証。

達成判定:
- clip 発動時刻 = weight が初めて (1.0 - 1e-10) を超えた時刻 (RK4, dt=0.01)
- 解析的予測 t = 20·ln(2) ≈ 13.8629 と一致 (誤差 < 0.1)
- t > t_clip で weight = 1.0 で安定

### KR-S4: 数値積分手法の収束性

Euler 法と RK4 の収束性を実測し、期待される次数と整合する。

達成判定:
- dt = {1.0, 0.5, 0.1, 0.05, 0.01} で各手法の最大誤差を測定
- log-log スケールで直線になる (収束次数の確認)
- Euler 法の傾きが約 1 (1 次収束)
- RK4 の傾きが約 4 (4 次収束)

### KR-S5: 単純化バイアス対策の機能確認 (Rule 8)

Sprint 1 で発見した単純化バイアスへの対策 (Rule 8) が Sprint 2 で機能。

達成判定:
- 完了報告で Rule 8 の必須テンプレート構造が守られている
- 「数値的に意外だった瞬間」セクションに 1 件以上の記述
- 「Devil's Advocate 視点」セクションに 3 点以上の記述
- 「微妙にずれた」または「完全に予期しなかった」サブセクションに 1 件以上の記述
  (ない場合は判断根拠を 3 行以上で説明)

## Sprint Backlog (16 タスク、推定工数 6-9 時間)

| # | タスク | 推定工数 | 状態 |
|---|--------|---------|------|
| 0 | doctest 実行の有効化 (pytest.ini 作成) | 5-10 分 | ✅ |
| 1 | CLAUDE.md (リポジトリルート) に Rule 8 追加 | 10-15 分 | ✅ |
| 2 | Sprint 1 docstring の NumPy スタイル準拠修正 | 15-20 分 | ✅ |
| 3 | Sprint 2 ディレクトリ構造の作成 | 10-15 分 | ✅ |
| 4 | SPRINT_OKR.md の作成 | 20-30 分 | ⏳ (本ファイル) |
| 5 | 解析解の実装 (src/analytical.py) | 15-20 分 | |
| 6 | Euler 法の実装 (src/integrators.py) | 20-30 分 | |
| 7 | RK4 法の実装 (src/integrators.py) | 30-45 分 | |
| 8 | ContinuousNode クラス (src/continuous_node.py) | 30-45 分 | |
| 9 | scenarios.py の新設 | 20-30 分 | |
| 10 | テスト実装 - 解析解との一致 (KR-S1, S2) | 30-45 分 | |
| 11 | テスト実装 - clip 付き挙動 (KR-S3) | 20-30 分 | |
| 12 | テスト実装 - 数値積分手法の収束性 (KR-S4) | 30-45 分 | |
| 13 | 可視化 (visualize.py) | 45-60 分 | |
| 14 | README.md の作成 | 30-45 分 | |
| 15 | 完了報告 (Rule 8 構造) | 30-45 分 | |

## Definition of Done

以下のすべてが満たされた時点で Sprint 2 は完了とする:

1. `pytest tests/ -v` で全テストが pass する
2. `pytest --junit-xml` で JUnit ログが results/logs/ に保存される
3. `python visualize.py` で 3 プロットが results/plots/ に生成される
4. `flake8 src/ tests/ visualize.py scenarios.py` でエラーなし
5. README.md が KR 達成を証拠付きで記述している
6. requirements.txt で全依存が pip freeze 形式で完全固定
7. KR-S1, KR-S2, KR-S3, KR-S4, KR-S5 達成
8. doctest が pytest 実行時に自動実行される (pytest.ini の --doctest-modules)
9. Sprint 1 docstring が NumPy スタイル準拠に修正されている (Notes 統合)
10. scenarios.py が動作し、visualize.py または test ファイルから利用される
11. .python-version ファイルが作成されている

## Out of Scope

### Sprint 1 から継続する Out of Scope

1. 温度変数や物理単位 (Sprint 3 以降)
2. PTC 効果の非線形数式 (Sprint 4 以降)
3. 複数ノード間の相互作用 (Sprint 5 以降)
4. GUI、対話的可視化、ダッシュボード
5. 設定ファイル (YAML, JSON)、コマンドラインオプション
6. ロギングフレームワーク (logging モジュール)
7. クラスの継承、抽象クラス
8. 並列処理、GPU 加速、Numba 等の最適化
9. 外部データベース、ファイル I/O 以外の永続化
10. 「より良い」実装としての過剰な refactoring 提案

### Sprint 2 特有の Out of Scope

11. soft saturation 関数 (sigmoid 等) の実装
12. scipy.integrate.solve_ivp 等の外部ライブラリへの依存
13. 適応的時間刻み (adaptive step size) の実装
14. 複数の入力パターン (任意の input(t) 関数) への一般化
15. 数値積分の精度に関する高度な分析
16. ContinuousNode と BinaryNode (Sprint 1) の統合

## Tripwires (即座に halt-and-review 発動)

1. Constitutional Commitments の違反が発見される
2. 主要な KR (S1, S2, S3) のいずれかが達成困難と判明
3. 選択肢 (c) → (b) の切り替え条件のいずれかに該当
   - 数値積分の精度が 1e-6 未満を達成できない
   - 二実装の保守コストが Sprint 2 予定時間の 50% を超える
   - テストロジックが複雑化しすぎる
4. 数学的予測 (例: t=13.863 で clip 発動) と実装結果が大きく乖離
5. 単純化バイアス対策 (Rule 8) が機能しない兆候が現れる
   (例: AI が再び「予期しない挙動: なし」のような報告をする)
6. その他、AI が独自判断で進めるべきでないと感じる事態

## R1 項目 (Sprint 1 deferred_issues.md より) の確定

Sprint 1 終了時に R1 (Retrospective で議論) として残された項目を、
Sprint 2 開始時に確定する。

| # | R1 項目 | Sprint 2 での確定 |
|---|---------|------------------|
| 1 | Python バージョン固定 | 案 A (.python-version 作成) |
| 2 | docstring スタイル | 方針 A (NumPy 標準準拠、カスタムセクションは Notes 内) |
| 3 | 共有モジュール scenarios.py の新設 | 新設 (タスク 9) |
| 4 | .claude/ ディレクトリ | ignore (Sprint 1 commit 時に root .gitignore に追加済み) |
| 5 | プロットアノテーションの厳密性 | 案 B (「t ≈ 13.86」のように approx マーク使用) |

## Mission OKR / Project OKR との関係

### Project OKR (Phase 1) への貢献

- **KR-P1 (7 段階シミュレーションの完了)**: Sprint 2 で進捗 2/7
- **KR-P5 (AI 支援開発の方法論的知見)**: Rule 8 の機能確認 (KR-S5) で直接貢献

### Mission OKR への貢献

- **KR-M1 (Substrate-Learning Rule Identity)**: 連続時間モデルへの拡張で物理的
  妥当性を増す (Newton 冷却則と同型)
- **KR-M2 (単極性更新の十分性)**: input ∈ {0, 1} の単極性で連続時間でも weight が
  動的に増減することを demonstration

### Constitutional Commitments との整合

- **Commitment 5 (Reproducibility First)**: venv + pip freeze + .python-version で
  環境再現性を厳格化
- **Commitment 6 (Halt-and-Review Default)**: 仕様の曖昧点 (5 質問) を実装前に確認
- **Commitment 8 (Honest Self-Assessment)**: Rule 8 で完了報告の単純化バイアスを
  構造的に防止
