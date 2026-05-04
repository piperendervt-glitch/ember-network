# Sprint 1 OKR: binary node, discrete time

ember-network シミュレーション開発 Phase の最初の Sprint。AAS の核心ルール「使うと増える、使わないと減る」を最も simple な離散時間 binary input モデルで動作確認する。

## Sprint Objective

AAS の核心ルール (使うと増える、使わないと減る) を最小の概念実装で動作確認する

## Sprint Key Results

### KR-S1: 一定入力下での weight 飽和

一定入力 `input=1` を 100 ステップ提示すると、weight が 1.0 に到達し、その後 1.0 で安定する。

達成判定:
- t=20 付近で weight が 1.0 に到達 (`abs(weight - 1.0) < 1e-10`)
- t=20 から t=100 の間 weight は 1.0 で一定 (clip 機能の確認)
- 最終 weight が 1.0 (誤差 < 1e-10)

### KR-S2: 入力停止後の線形減衰

一定入力 `input=1` を 50 ステップ後、`input=0` を 50 ステップ提示すると、t=50 から線形減衰 (傾き -0.05)、t=70 付近で weight が 0 に到達、t=70 から t=100 で weight は 0 で一定。

達成判定:
- t=50 で weight = 1.0
- t=51 から t=70 の間、weight が傾き -0.05 で線形に減衰
- t=70 で weight = 0 (clip 発動)
- t=70 から t=100 で weight は 0 で一定

### KR-S3: 完全な再現性

5 つの異なるランダムシードで完全に同じ結果が再現される (現在のモデルは決定論的)。

達成判定:
- `random.seed()` と `np.random.seed()` を 5 つの異なる値で固定し、同一シナリオを実行
- 全シードで weight 時系列が bit-perfect に一致 (`numpy.array_equal`)

## Sprint Backlog

| # | タスク | Acceptance Criteria |
|---|--------|---------------------|
| 1 | venv 作成と依存固定 | `.venv/` 作成、`requirements.txt` (pip freeze 形式) コミット |
| 2 | `src/binary_node.py`: BinaryNode クラス実装 | init/update/weight/reset の 4 メソッド、NumPy スタイル docstring |
| 3 | `tests/test_basic.py`: 基本動作テスト | 初期化、更新、範囲外防止、ValueError の 4 系統 |
| 4 | `tests/test_constant_input.py`: KR-S1 検証テスト | 100 ステップで weight=1.0 到達と安定性 |
| 5 | `tests/test_input_cessation.py`: KR-S2 検証テスト | 線形減衰と 0 到達 |
| 6 | `tests/test_reproducibility.py`: KR-S3 検証テスト | 5 シード bit-perfect 一致 |
| 7 | `visualize.py`: 3 プロット生成 | `plot_constant_input.png`, `plot_input_cessation.png`, `plot_reproducibility.png` |
| 8 | `pytest --junit-xml` でログ保存 | `results/logs/pytest_results.xml` 生成、全テスト pass |
| 9 | flake8 チェック | `src/`, `tests/`, `visualize.py` でエラーなし |
| 10 | `README.md` 作成 | Sprint 1 Objective、KR 達成状況、設計サマリ、結果、学んだこと、Sprint 2 引継ぎ |

## Definition of Done

以下のすべてが満たされた時点で Sprint 1 は完了とする:

1. `pytest tests/ -v` で全テストが pass する
2. `pytest --junit-xml=results/logs/pytest_results.xml` で JUnit 形式ログが保存される
3. `python visualize.py` で 3 つのプロットが `results/plots/` に生成される
4. `flake8 src/ tests/ visualize.py` でエラーなし
5. `README.md` が KR-S1, KR-S2, KR-S3 の達成を証拠付きで記述している
6. `requirements.txt` で全依存が固定されている
7. KR-S1, KR-S2, KR-S3 の達成判定基準を全て満たす

## Out of Scope (Sprint 1 では実装しない)

仕様外の追加実装が魅力的に見えても、本 Sprint には組み込まない。提案がある場合は `lab_notebook/next_project_candidates.md` に記録のみ。

1. 連続時間モデル (Sprint 2 で扱う)
2. 温度変数や物理単位 (Sprint 3 以降)
3. PTC 効果の非線形数式 (Sprint 4 以降)
4. 複数ノード間の相互作用 (Sprint 5 以降)
5. GUI、対話的可視化、ダッシュボード
6. 設定ファイル (YAML, JSON)、コマンドラインオプション
7. ロギングフレームワーク (logging モジュール)
8. クラスの継承、抽象クラス
9. 並列処理、GPU 加速、Numba 等の最適化
10. 外部データベース、ファイル I/O 以外の永続化
11. 「より良い」実装としての過剰な refactoring

## Mission OKR / Project OKR との関係

### Project OKR (Phase 1 シミュレーション開発) への貢献

- **KR-P1 (7 段階シミュレーションの完了)**: Sprint 1 はその第 1 段階。本 Sprint の Definition of Done を満たすことで KR-P1 の進捗 1/7 を達成。
- **KR-P5 (AI 支援開発の方法論的知見)**: 本 Sprint で AI 関連メトリクス (`ai_metrics/sprint-01_ai_log.md`) を記録する。

### Mission OKR への貢献

- **KR-M1 (Substrate-Learning Rule Identity の概念実証)**: 本 Sprint は最小の概念モデル (温度・物理単位なし) なので、Mission KR への直接貢献は限定的。後続 Sprint の基盤となる。
- **KR-M2 (単極性更新の十分性)**: `input ∈ {0, 1}` の単極性更新で weight が増減する動作を確認することで、双極性更新が不要であることの基礎的 demonstration になる。

### Constitutional Commitments との整合

- **Commitment 5 (Reproducibility First)**: KR-S3 (完全な再現性) で直接的に対応。venv + `requirements.txt` 完全固定で環境再現性も保証。
- **Commitment 3 (Bounded Scope)**: Out of Scope を明示し、scope creep を防止。
- **Commitment 6 (Halt-and-Review Default)**: 仕様の解釈に迷う点は実装前に質問し、独断で進めない。

## Tripwires (発動時に halt して再評価)

以下のいずれかが発生した場合、Sprint を一旦止めて再評価する:

1. KR-S3 (再現性) で bit-perfect 一致が得られない → 決定論性の前提が崩れたことを意味する。実装ミスの可能性を最優先で調査。
2. KR-S1 / KR-S2 の数値予測と実測値が乖離 → 数学モデルの理解または実装に誤りがある可能性。
3. Out of Scope の項目が「必要に思える」事態 → 仕様の不備または scope の再検討が必要な可能性。
