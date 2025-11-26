# 履歴書PDF生成器 - AIOCR テスト素材用

OCR（光学文字認識）システムのテスト用に、様々な品質バリエーションを持つ履歴書PDFを自動生成するツール。

## 概要

このツールは、OCRの精度測定やモデル評価のためのテストデータセットを作成する。生成される履歴書PDFには、実際のスキャン文書で発生しうる様々な劣化パターンが含まれており、OCRシステムの境界ケースや弱点を特定するのに役立つ。

## 生成されるバリエーション

| No | 種類 | 難易度 | 説明 |
|----|------|--------|------|
| 1-2 | standard | easy | きれいな明朝体（基準用） |
| 3-4 | handwritten | medium | 手書き風フォント |
| 5-6 | faded | medium | 薄い文字（印刷かすれ風） |
| 7-8 | tilted | medium | 1.5〜3度の傾き（スキャン歪み風） |
| 9-10 | noisy | hard | 汚れ・シミ風ノイズ |
| 11-12 | blurred | hard | ぼかし処理（低解像度風） |
| 13-14 | heavy_lines | medium | 太い罫線（文字と被り気味） |
| 15-16 | small_font | medium | 小さいフォント |
| 17-18 | mixed_font | medium | ゴシック+明朝混在 |
| 19-20 | complex | hard | 薄字+傾き+ノイズの複合劣化 |

## 出力ファイル

```
outputs/
├── pdfs/
│   ├── resume_001_standard.pdf
│   ├── resume_002_standard.pdf
│   ├── resume_003_handwritten.pdf
│   └── ... (計20ファイル)
└── dataset.jsonl
```

### dataset.jsonl の形式

```json
{"input_pdf": "gs://your-bucket/resumes/resume_001_standard.pdf", "target": "氏名: 山田太郎\n生年月日: 1990年1月1日\n住所: 東京都渋谷区1-2-3", "variation": "standard", "difficulty": "easy"}
```

| フィールド | 説明 |
|-----------|------|
| input_pdf | PDFファイルのパス（GCSプレフィックスは変更可能） |
| target | OCRで抽出されるべき正解テキスト |
| variation | バリエーション種別 |
| difficulty | OCR難易度（easy / medium / hard） |

## セットアップ

### 必要環境

- Python 3.12+
- IPAフォント（IPAexMincho, IPAexGothic）

### 1. リポジトリをクローン

```bash
git clone <repository-url>
cd resume-pdf-generator
```

### 2. 仮想環境を作成

```bash
python3 -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate   # Windows
```

### 3. 依存ライブラリをインストール

```bash
pip install -r requirements.txt
```

### 4. 日本語フォントをインストール

**Ubuntu/Debian:**
```bash
sudo apt install fonts-ipaexfont
```

**Mac (Homebrew):**
```bash
brew install font-ipaexfont
```

**Windows:**

[IPAフォント公式サイト](https://moji.or.jp/ipafont/)からダウンロードしてインストール。

### 5. フォントパスを確認・設定

```bash
fc-list | grep -i ipa
```

出力例：
```
/usr/share/fonts/opentype/ipaexfont-mincho/ipaexm.ttf: IPAexMincho,IPAex明朝:style=Regular
/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf: IPAexGothic,IPAexゴシック:style=Regular
```

パスが異なる場合は `generate_resumes.py` の以下を修正：

```python
FONT_MINCHO = "/your/path/to/ipaexm.ttf"
FONT_GOTHIC = "/your/path/to/ipaexg.ttf"
```

## 使い方

### 基本実行

```bash
python generate_resumes.py
```

### GCSバケットパスを変更する場合

`generate_resumes.py` の `main()` 関数内を修正：

```python
gcs_bucket_prefix = "gs://your-actual-bucket/path"
```

### 出力先を変更する場合

`generate_resumes.py` の定数を修正：

```python
OUTPUT_DIR = Path("your/output/path/pdfs")
JSONL_PATH = Path("your/output/path/dataset.jsonl")
```

## カスタマイズ

### バリエーションの個数を変更

`generate_all_resumes()` 関数内の `variations` リストを編集：

```python
variations = [
    (VariationType.STANDARD, 5),  # 5個に増やす
    (VariationType.NOISY, 10),    # 10個に増やす
    # ...
]
```

### 新しいバリエーションを追加

1. `VariationType` Enumに新しい種別を追加
2. `get_variation_config()` に設定を追加
3. `_get_difficulty()` に難易度を追加

### ダミーデータを拡張

`LAST_NAMES`, `FIRST_NAMES_MALE`, `FIRST_NAMES_FEMALE`, `PREFECTURES` リストに追加。

## 参考

- [IPAフォント](https://moji.or.jp/ipafont/) - 日本語フォント
- [Pillow](https://pillow.readthedocs.io/) - 画像処理ライブラリ
- [ReportLab](https://www.reportlab.com/) - PDF生成ライブラリ
