# ember-network

PTC (Positive Temperature Coefficient) 物理 AAS (Adaptive Artificial Synapse) の deterrence-oriented な参照実装を確立する研究プロジェクト。

熱物理が学習則を直接的に体現する物理基板を、シミュレーション、電子部品仮実装、3D プリント物理基板の段階で開発する。

## プロジェクト名の由来

`ember` は燃え尽きた後も静かに熱を保ち続ける炭火 (燠、おき火) を指す。電流が流れた経路に残る熱、それが時間とともに自然に冷めていく構造、再び熱が加わることで刻まれる記憶。これらが ember-network の核心である。

## 研究の哲学

このプロジェクトは AI capability の追求ではなく、制御不能 AI への deterrence (抑止) としての AI 開発を目指す。物理散逸、遅延、スケール限界を「制限を物理が保証する」設計原理として採用する。

## 研究の核心的主張

1. **Substrate-Learning Rule Identity**: PTC 効果と自然冷却の組み合わせが、Hebbian 学習則を物理現象として直接体現する。学習則を実装するのではなく、学習則を体現する物理基板。

2. **単極性更新の十分性**: memristor 研究の中心的前提である双極性 (能動的な正負両方向の書き込み) は、AAS の自然忘却ルール下では不要。時間経過 (冷却) が下げる役割を担う。

3. **物理的 deterrence**: 重みは熱でしか保持されず、電源切断で揮発する。スケールが熱拡散で物理的に頭打ちになる。観察可能性 (重み分布が物理的に可視化される) が保証される。これらが AI 安全研究において新しい paradigm を提供する。

## 研究フェーズ

```
Phase 1: ソフトウェアシミュレーション開発  (現在進行中)
   ↓
Phase 2: 電子部品による仮実装
   ↓
Phase 3: 3D プリント物理基板の実装
   ↓
Phase 4: 論文化と公開 (Zenodo + note)
```

## ディレクトリ構造

```
ember-network/
├── README.md                       # 本ファイル
├── MISSION_OKR.md                  # Mission OKR
├── PROJECT_OKR.md                  # Project OKR
├── CONSTITUTION.md                 # Constitutional Commitments
├── CLAUDE.md                       # AI 利用ガイドライン
├── sprint-00-okr-setup/            # Sprint 0: 体制確立
├── sprint-01-binary-node/          # Sprint 1: 最小ルール実装
├── sprint-02-continuous-time/      # Sprint 2: 連続時間モデル
├── sprint-03-temperature/          # Sprint 3: 温度変数の導入
├── sprint-04-ptc-effect/           # Sprint 4: PTC 効果の現実的モデル
├── sprint-05-cross-talk/           # Sprint 5: 複数経路と相互作用
├── sprint-06-aas-dynamics/         # Sprint 6: AAS 動作の機能シミュレーション
├── sprint-07-physical-calibration/ # Sprint 7: 物理パラメータ校正
├── sprint-08-scaling/              # Sprint 8: スケーリング限界 (任意)
├── lab_notebook/                   # 日次研究ジャーナル
└── ai_metrics/                     # AI 利用メトリクス
```

## 研究方法論

### OKR + アジャイル統合運用

研究は以下の三層 OKR で構造化される。

- **Mission OKR**: 研究プログラム全体の方向性 (`MISSION_OKR.md`)
- **Project OKR**: 各 Phase の具体的目標 (`PROJECT_OKR.md`)
- **Sprint OKR**: 各 Sprint の達成目標 (各 Sprint ディレクトリの `SPRINT_OKR.md`)

各 Sprint はアジャイルの短サイクル (1-7 営業日) で運用される。

### Preregistration

各 Phase の開始前に、仮説と分析方法を preregistration として固定する。これにより研究の方法論的厳密さを確保する。

### Constitutional Commitments

研究全体を通じて守る原則を `CONSTITUTION.md` に明示。各判断時に整合性を確認する。

## AI 支援開発の方法論

このプロジェクトは AI 支援開発における OKR の有効性検証を副次的目的としても持つ。`CLAUDE.md` で AI 利用ガイドラインを明示し、AI 関連メトリクスを `ai_metrics/` に継続的に記録する。

## 公開方針

個人研究者として、以下のプラットフォームを通じて研究成果を発信する。

- **GitHub**: コード、シミュレーション結果、CAD ファイル、ドキュメントの継続的公開
- **Zenodo**: 論文 preprint、研究マイルストーンのアーカイブ、DOI 取得
- **note**: 一般読者向けの研究紹介記事

伝統的な査読付きジャーナルへの submit は本プロジェクトの達成判定には含まないが、機会があれば検討する。

## 関連プロジェクト

- `multimodal-aas-bird`: AAS proof-of-concept の先行研究
- `fiberfeel-rig`: POF 圧力センサ研究 (preregistration 方法論を共有)
- TRUSS framework: 多層 AI 安全フレームワーク
- Tsukumogami Framework: 分散知能哲学

## ライセンス

(Robosheep さんの公開方針に応じて記述。例: MIT License、CC BY 4.0、Apache 2.0 等)

## 著者

Robosheep / pipe_render / 村下勝真

ORCID: (Robosheep さんの ORCID URL)

## 引用

本プロジェクトの成果を引用する際は以下を参照:

(将来 Zenodo に公開される論文の DOI および引用情報をここに追加)
