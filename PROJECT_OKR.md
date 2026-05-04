# Project OKR: ember-network シミュレーション開発 (Phase 1)

ember-network プロジェクトの最初の Phase。PTC 物理 AAS の理論モデルを 7 段階のシミュレーションで構築し、preregistration の定量的基盤を生成する。

## Project Objective

PTC 物理 AAS の理論的予測を確立し、preregistration の定量的基盤を生成する

## Project Key Results

### KR-P1: 7 段階シミュレーションの完了

各 Sprint (Sprint 1-7) で Sprint OKR の成功基準を達成する。

達成判定:
- Sprint 1: binary node, discrete time
- Sprint 2: continuous time and time constants
- Sprint 3: temperature variable introduction
- Sprint 4: realistic PTC effect model
- Sprint 5: multi-path cross-talk
- Sprint 6: AAS dynamics simulation
- Sprint 7: physical parameter calibration

各 Sprint の Definition of Done を満たし、tripwires に該当する状況がない。

### KR-P2: 物理パラメータ校正された予測値の生成

物理パラメータ (PLA カーボンの実物性値) で校正されたシミュレーションが、実物実験での測定値の予測値と信頼区間を提供する。

達成判定:
- PLA カーボンの物性値が文献データから確定 (出典明記)
- 単一個体の挙動が物理単位 (Ω, °C, s, mm) で予測される
- 100 個体の確率的シミュレーションで個体差の統計分布が生成される
- 検出力分析により必要なサンプル数が定量化される
- 実物実験での測定値の予測範囲 (信頼区間) が確定する

### KR-P3: Preregistration への組み込み

シミュレーション結果から導出された定量的予測を、preregistration prereg-v1 に組み込む。

達成判定:
- prereg-v1 の H0-H4 各仮説に対する定量的予測値が記入される
- 必要サンプル数が検出力分析から確定される
- 統計分析計画 (Cohen's d 計算法、有意水準) が確定される
- prereg-v1 タグが GitHub リポジトリに打たれる

### KR-P4: Time-box 遵守

研究プロジェクトを 4-6 週間 (24-29 営業日) の time-box 内に完了する。

達成判定:
- Sprint 0-7 の合計実行時間が time-box 内
- time-box 超過時は halt-and-review が発動される
- 時間記録が継続的に取られる

### KR-P5: AI 支援開発の方法論的知見の生成

AI 支援開発における OKR + アジャイルの有効性を継続的に評価し、方法論的知見を文書化する。

達成判定:
- 各 Sprint で AI 関連メトリクスが記録される (`ai_metrics/sprint-XX_ai_log.md`)
- specification 違反率、hallucination 率、scope creep 率が定量化される
- Project 終了時に AI 支援開発の OKR 有効性評価がまとめられる
- 効果的だった AI 利用パターン、阻害的だったパターンの分析が文書化される

## Project の境界画定 (Scope)

### In Scope (やること)

1. PTC 物理 AAS の理論モデルの 7 段階実装
2. Joule 加熱、熱拡散、PTC 効果、Hebbian 学習則の物理シミュレーション
3. 1 入力 → 3 並列 PTC の AAS 動作の理論的予測
4. 物理パラメータでの校正と個体差モデル化
5. preregistration prereg-v1 への定量予測値の提供
6. AI 支援開発の方法論的観察と記録

### Out of Scope (やらないこと)

1. 4 ノード以上の系の実装 (Mission の最小実装範囲を超える)
2. 性能最適化 (GPU 加速、並列化等)
3. 実物実験の代替 (シミュレーションは実物実験を準備する手段)
4. GUI、可視化ダッシュボードの構築 (matplotlib の標準で十分)
5. Paper B 以降の拡張 (世代間転写、モジュラー化、embodied 統合等)
6. 他の AI フレームワーク (PyTorch DNN 等) との比較
7. メタ的論文 (Paper W スケール選択、Paper R 同一性論など) の本文執筆

## Sprint への分解

```
Sprint 0: OKR 体制確立 (1-2 営業日)
   ↓
Sprint 1: binary node, discrete time (1 営業日)
   ↓
Sprint 2: 連続時間と時定数 (1 営業日)
   ↓
Sprint 3: 温度変数の導入 (2 営業日)
   ↓
Sprint 4: PTC 効果の現実的モデル (3 営業日)
   ↓
Sprint 5: 複数経路と cross-talk (4 営業日)
   ↓
Sprint 6: AAS 動作のシミュレーション (5 営業日)
   ↓
Sprint 7: 物理パラメータ校正と個体差 (7 営業日)
   ↓ (任意)
Sprint 8: スケーリング限界 (5 営業日)
```

各 Sprint は前 Sprint の出力を input として使用する。並列実行はしない (WIP limit)。

## Mission OKR との関係

Project OKR は Mission OKR の達成に向けた最初のステップ。各 KR の Mission KR への貢献:

- KR-P1 → Mission KR-M1, KR-M2 (理論モデルの確立)
- KR-P2 → Mission KR-M3 (物理的特性の予測)
- KR-P3 → Mission KR-M5 (preregistration 方法論)
- KR-P4 → 研究の現実性の確保
- KR-P5 → AI 支援開発の方法論的知見 (副次的だが重要)

## Halt-and-Review トリガー

以下のいずれかに該当する場合、Project を一旦止めて再評価する:

1. Constitutional Commitments の違反が発見される
2. 主要な KR が 2 つ以上連続して未達
3. Time-box を 50% 以上超過
4. Scope creep が累積し、当初の Project Objective から大きく逸脱
5. 研究が Robosheep さんの本業や健康に深刻な影響を及ぼす
6. 研究方針 (deterrence-oriented) との根本的不整合が発見される
7. Sprint 5 の tripwire (Hebbian 局所性が物理的に不可能) が発動

## Project 完了の定義

Project が完了するのは以下のすべてが満たされた時:

1. KR-P1 から KR-P5 のすべてが達成される
2. Mission OKR との整合性が確認される
3. Project Retrospective が実施され、次 Phase (電子部品仮実装) への引き継ぎ事項が明示される
4. 結果が GitHub に公開される
