# Potential Risk Log (潜在リスクログ)

このファイルは ember-network プロジェクトで認識された潜在リスクを追跡する。
Rule 10.6 (検知確率 90% KPI と潜在リスクログ) および Commitment 9 (自己参照
ループの残存リスクの管理) に基づいて運用する。

各 Sprint Retrospective で全エントリーを再評価する。

形式: ハイブリッド形式 (Sprint 2 Retrospective で確定した選択肢 Z)
- ファイル先頭に概要表 (一覧)
- 詳細セクション (各 PRL の完全記述)

---

## 概要表

| ID | カテゴリ | 事象 (要約) | 発見 Sprint | 対処状況 | 関連 Commitment |
|------|------|------|------|------|------|
| PRL-001 | 単純化バイアス | Sprint 1 完了報告で「予期しない挙動: なし」と単純化された | Sprint 1 | 対処済み (Rule 8) | C8 |
| PRL-002 | 仕様の見落とし | Sprint 2 Planning で 6 件の判断項目が未明示 | Sprint 2 | 対処方針確定 | C8 |
| PRL-003 | 数値計算の制約 | RK4 が不連続な右辺で 4 次精度を失う | Sprint 2 | 対処済み (scenarios.py) | C5 |
| PRL-004 | 物理モデルの境界 | 連続時間モデル dw/dt=-β·w は w=0 を漸近境界とする | Sprint 2 | 対処済み (positivity 不変量) | C5 |
| PRL-005 | 自己参照ループ | doctest の期待値が実装結果由来 | Sprint 2 | 対処方針確定 (Rule 10.1) | C8, C9 |
| PRL-006 | 自己参照ループ | Claude Code が認識したケースのみテストされる | Sprint 2 | 対処方針確定 (Rule 10.5) | C9 |
| PRL-007 | 自己参照ループ | Claude Code 自身による Devil's Advocate は外部視点ではない | Sprint 2 | 対処方針確定 (Rule 10.5) | C9 |
| PRL-008 | 自己参照ループ | Halt-and-Confirm の推奨が承認される構造 | Sprint 2 | 部分検証済み (Sprint 3 Step D 事例) | C9 |
| PRL-009 | 自己参照ループ + 運用設計 | 外部 AI ファイルの偶発的可視 (pytest 自動収集) | Sprint 3 | 部分対処 (pytest.ini exclude) | C9 |
| PRL-010 | Sprint Planning の見落とし + 外部視点 | 外部 AI 4/6 が fractional input を自然視 | Sprint 3 | Sprint 4 で再評価 | C3, C9 |
| PRL-011 | API 設計 + テストカバレッジ | 非物理初期状態 (T < T_env) の検証手段なし | Sprint 3 | Sprint 4 で再評価 | C3 |

---

## 詳細セクション

### PRL-001: 単純化バイアス

- **発見日**: Sprint 1 完了時
- **カテゴリ**: 単純化バイアス
- **事象**: Sprint 1 完了報告で「予期しない挙動: なし」と単純化された
- **発見の経緯**: Self Review (Sprint 1 完了後)
- **影響範囲**: プロジェクト全体の方法論
- **対処状況**: 対処済み (Sprint 2 で Rule 8 を導入)
- **残存リスク**: Rule 8 自体が形式化される可能性 (Sprint 2 完了報告
  Devil's Advocate #5 参照)
- **関連 Commitment**: Commitment 8 (Honest Self-Assessment)
- **次回再評価**: 各 Sprint Retrospective

### PRL-002: 仕様の見落とし (Sprint 2 Planning 6 件)

- **発見日**: Sprint 2 Planning ~ Sprint 2 実装中
- **カテゴリ**: 仕様の見落とし
- **事象**: Sprint 2 Planning で 6 件の判断項目を明示せず (doctest 例の不
  整合、dt のデフォルト、scenarios.py の戻り値、t_clip の操作的定義、RK4
  の不連続関数問題、連続時間 lower bound)
- **発見の経緯**: Sprint 2 Halt-and-Confirm
- **影響範囲**: Sprint 2 の実装プロセス
- **対処状況**: 対処方針確定 (Sprint 3 Planning で改善)
- **残存リスク**: Sprint 3 Planning でも見落としが発生する可能性
- **関連 Commitment**: Commitment 8
- **次回再評価**: Sprint 3 Retrospective

### PRL-003: RK4 の不連続点問題

- **発見日**: Sprint 2 実装中
- **カテゴリ**: 数値計算の制約
- **事象**: RK4 が不連続な右辺 (input の切替) で 4 次精度を失う
- **発見の経緯**: Sprint 2 Halt-and-Confirm
- **影響範囲**: 当該 Sprint で対処、Sprint 3 以降の入力切替シナリオ全般
- **対処状況**: 対処済み (scenarios.py 経由で 1 ステップ内 input 固定)
- **残存リスク**: Sprint 3 で温度変数導入時に類似問題が発生する可能性
- **関連 Commitment**: Commitment 5 (Reproducibility First)
- **次回再評価**: Sprint 3 完了時

### PRL-004: 連続時間モデルの lower bound 漸近性

- **発見日**: Sprint 2 実装中
- **カテゴリ**: 物理モデルの境界
- **事象**: 連続時間モデル dw/dt = -β·w は w=0 を漸近境界とする
  (離散時間の Sprint 1 と異なる)
- **発見の経緯**: Sprint 2 Halt-and-Confirm
- **影響範囲**: Sprint 3 の物理モデル設計に直接影響
- **対処状況**: 対処済み (テスト変更、Sprint 3 で物理的不変量 positivity
  として preregister)
- **残存リスク**: 同種の「離散 vs 連続」の混同が他の場面で発生する可能性
- **関連 Commitment**: Commitment 5
- **次回再評価**: Sprint 3 Retrospective

### PRL-005: doctest の自己参照

- **発見日**: Sprint 2 完了報告時
- **カテゴリ**: 自己参照ループ
- **事象**: doctest の期待値が実装結果由来 (Sprint 2 完了報告 Devil's
  Advocate #4)
- **発見の経緯**: Sprint 2 完了報告の Devil's Advocate セクション
- **影響範囲**: プロジェクト全体のテスト方法論
- **対処状況**: 対処方針確定 (Sprint 3 で Rule 10.1 doctest と pytest
  の分離)
- **残存リスク**: Sprint 3 でも完全に分離しきれない可能性
- **関連 Commitment**: Commitment 8, Commitment 9
- **次回再評価**: Sprint 3 Retrospective

### PRL-006: テストカバレッジが Claude Code 認識依存

- **発見日**: Sprint 2 Retrospective
- **カテゴリ**: 自己参照ループ
- **事象**: Claude Code が認識したケースのみテストされる
- **発見の経緯**: Sprint 2 Retrospective での議論
- **影響範囲**: プロジェクト全体のテスト方法論
- **対処状況**: 対処方針確定 (Sprint 3 で外部 AI 3 段階導入、Rule 10.5)
- **残存リスク**: 外部 AI も認識していない盲点が残る
- **関連 Commitment**: Commitment 9
- **次回再評価**: Sprint 3 Retrospective

### PRL-007: Devil's Advocate が自己批判

- **発見日**: Sprint 2 Retrospective
- **カテゴリ**: 自己参照ループ
- **事象**: Claude Code 自身による Devil's Advocate は外部視点ではない
- **発見の経緯**: Sprint 2 Retrospective での議論
- **影響範囲**: プロジェクト全体の自己批判の質
- **対処状況**: 対処方針確定 (Sprint 3 で外部 AI 3 段階導入)
- **残存リスク**: 外部 AI も Claude 系列とは別の偏見を持つ可能性
- **関連 Commitment**: Commitment 9
- **次回再評価**: Sprint 3 Retrospective

### PRL-008: Halt-and-Confirm の推奨が承認される構造

- **発見日**: Sprint 2 Retrospective (Devil's Advocate #5)
- **カテゴリ**: 自己参照ループ
- **事象**: Sprint 2 で 2 つの Halt-and-Confirm で Claude Code、設計支援役
  Claude、Robosheep の判断がすべて一致した。「Claude の推奨を Robosheep
  に承認させる構造」になっている可能性
- **発見の経緯**: Claude Code の Devil's Advocate #5 での自己批判
- **影響範囲**: プロジェクト全体の判断プロセス
- **対処状況**: 部分検証済み (Sprint 3 Step D 事例で部分的反証)
- **Sprint 3 Step D での部分検証**:
  - 私 (Claude Code) の提示した 4 選択肢: Option A (skip)、B
    (adapt to input=1)、C (Sprint 3 spec 拡張)、D (ハイブリッド)
  - Robosheep の判断: **Option E** (新規) — 「Sprint 3 では skip、
    Sprint 4 で PRL-010 として再評価」という時間軸を組み込んだ構造
  - これは「Claude が想定したオプションの中から Robosheep が選ぶ」構造
    ではなく「Robosheep が独立に新オプションを設計する」構造
  - 完全反証ではない (Robosheep は Claude の提示を起点に Option E を
    構築しているため微妙な依存関係が残る) が、PRL-008 が指摘した懸念
    への部分的反証として記録
- **残存リスク**: Sprint 4 以降で同様の構造的反証事例が継続するか観察
- **検証方法**: Sprint 4 以降で「Claude の推奨に対し Robosheep が独立に
  新オプションを提示する事例」が継続するか観察
- **関連 Commitment**: Commitment 9
- **次回再評価**: Sprint 4 Retrospective

### PRL-009: 外部 AI ファイルの偶発的可視 (Sprint 3 で発見)

- **発見日**: Sprint 3 Step C 中
- **カテゴリ**: 自己参照ループ + 運用設計の隠れた前提
- **事象**: external_ai_responses/ の .py ファイルが pytest の自動収集で
  ImportError を起こし、エラーメッセージから Claude Code がファイル名と
  import 行を偶発的に観察
- **発見の経緯**: Sprint 3 Step C 完了報告
- **影響範囲**: Sprint 3 の運用設計、Sprint 4 以降の同種運用
- **対処状況**: 部分的に対処 (pytest.ini で構造的 exclude)
- **残存リスク**:
  - Claude Code の「中身を見ていない」という自己報告の検証手段が内省のみ
  - 同種の偶発的可視が他のツール (flake8、IDE 等) で発生する可能性
- **関連 Commitment**: Commitment 9
- **検証方法**: Sprint 3 完了時、Robosheep が中身を確認した時に偶発的可視
  の影響の有無を事後評価
- **次回再評価**: Sprint 3 Retrospective

### PRL-010: 外部 AI による fractional input の独立提案

- **発見日**: Sprint 3 Step D 中
- **カテゴリ**: Sprint Planning の見落とし + 外部視点の発見
- **事象**: 6 つの外部 AI テストファイルのうち、4 つ以上が fractional
  input (input ∈ [0, 1]) を自然視するテストを提案。Sprint 3 OKR では
  input ∈ {0, 1} を Out of Scope (項目 17) として明示していたが、これは
  外部 AI 視点では「ember-network 特有の判断」と認識されなかった可能性。
- **発見の経緯**: Sprint 3 Step D での外部 AI ファイル読了時
- **影響範囲**:
  - Sprint 3 では Option E に基づき該当テストを skip
  - Sprint 4 Planning で fractional input サポートを再評価
- **対処状況**: Sprint 4 への引き継ぎ事項として記録
- **残存リスク**:
  - fractional input の Out of Scope 化が ember-network の研究方針
    (deterrence-oriented) と整合するかの判断が未確定
  - 同種の「Claude 系列共通の盲点」が他の場面でも存在する可能性
  - dt=0 の扱い (ChatGPT I Test 8): Sprint 3 では ValueError、Sprint 4
    以降で no-op 許容を検討
- **Hypothesis max_examples の増強検討** (Sprint 3 Step E 時に追記):
  - 現状: bounded property test で `max_examples=40` (Step D 追加)
  - 引き継ぎ: Sprint 4 で `max_examples=200` への増強と他の不変量
    (monotonicity 等) への展開を検討
  - 動機: 実時間 ~0.5 sec で済むため、現状は防御的すぎる設定
  - 注意: PTC 非線形性 (Sprint 4 で導入) 後は Hypothesis の検証力が
    更に重要になる
- **関連 Commitment**: Commitment 3 (Bounded Scope), Commitment 9
- **検証方法**: Sprint 4 Planning で再評価
- **次回再評価**: Sprint 4 Planning

### PRL-011: 非物理初期状態の検証

- **発見日**: Sprint 3 Step D
- **カテゴリ**: API 設計 + テストカバレッジ
- **事象**: 外部 AI が「T < T_env からの復帰」を検証するテストを提案
  (ChatGPT II Test 4: T = -1.0 開始; ChatGPT II Test 9 後半: T_low =
  -0.5)。Sprint 3 の現実装は `_T = T_env` 固定で、負の初期 T を直接設定
  不可。
- **発見の経緯**: Sprint 3 Step D での外部 AI ファイル読了時
- **影響範囲**: Sprint 3 では skip、Sprint 4 以降で T_initial パラメータ
  の追加を検討
- **対処状況**: Sprint 3 では skip、Sprint 4 以降で T_initial パラメータ
  の追加を検討
- **関連 Commitment**: Commitment 3
- **次回再評価**: Sprint 4 Planning

---

## 変更履歴

- 2026-05-04 (Sprint 3 開始時、初版作成): PRL-001 から PRL-008 を Sprint 2
  Retrospective の確定版として記載。ハイブリッド形式 (選択肢 Z) を採用。

## 運用ノート

- 各 PRL の対処は Sprint 完了時にステータスを更新する
- 「対処済み」は当該 Sprint で具体的対策が完了した場合
- 「対処方針確定」は方針は決まったが効果検証は次 Sprint 以降
- 「監視中」は能動的対策が困難で、観察によりリスク顕在化を検知する場合
- Sprint 3 中に新規発見された潜在リスクは PRL-009 以降として追加する
- 認識していない盲点は本ログに含まれない (PRL-006, PRL-007 の限界)
