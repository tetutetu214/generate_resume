"""
履歴書PDF生成器 - AIOCR テスト素材用

このスクリプトは、OCR（光学文字認識）システムのテスト用に、
様々な品質バリエーションを持つ履歴書PDFを自動生成する。

生成されるバリエーション:
    - standard: 標準的なきれいな履歴書（基準用）
    - handwritten: 手書き風フォント
    - faded: 薄い文字（印刷かすれ風）
    - tilted: 傾いた文字（スキャン歪み風）
    - noisy: ノイズ入り（汚れ・シミ風）
    - blurred: ぼかし処理（低解像度風）
    - heavy_lines: 太い罫線（文字と被り気味）
    - small_font: 小さいフォント
    - mixed_font: ゴシックと明朝の混在
    - complex: 複合劣化（薄字+傾き+ノイズ）

出力:
    - outputs/pdfs/ : 生成されたPDFファイル（20個）
    - outputs/dataset.jsonl : 入力パスと正解データのペア

使用方法:
    $ python generate_resumes.py

必要なライブラリ:
    - reportlab: PDF作成
    - Pillow: 画像処理（ノイズ、ぼかし、回転など）

必要なシステムフォント:
    - IPAexMincho（IPA明朝）
    - IPAexGothic（IPAゴシック）
    Ubuntu: sudo apt install fonts-ipaexfont
    Mac: brew install font-ipaexfont
"""
import json
import random
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


# =============================================================================
# フォント設定
# =============================================================================
# フォントパスは環境に応じて変更すること
# 確認コマンド: fc-list | grep -i ipa
FONT_MINCHO = "/usr/share/fonts/opentype/ipaexfont-mincho/ipaexm.ttf"
FONT_GOTHIC = "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf"

# =============================================================================
# 出力先設定
# =============================================================================
OUTPUT_DIR = Path("outputs/pdfs")
JSONL_PATH = Path("outputs/dataset.jsonl")


class VariationType(Enum):
    """
    PDFのバリエーション種別を定義する列挙型

    OCRテストにおいて、様々な品質の入力に対する認識精度を
    測定するために、複数のバリエーションを用意している。
    """

    STANDARD = "standard"        # 標準（きれいな状態）
    HANDWRITTEN = "handwritten"  # 手書き風
    FADED = "faded"              # 薄い文字
    TILTED = "tilted"            # 傾き
    NOISY = "noisy"              # ノイズ（汚れ）
    BLURRED = "blurred"          # ぼかし
    HEAVY_LINES = "heavy_lines"  # 太い罫線
    SMALL_FONT = "small_font"    # 小さい文字
    MIXED_FONT = "mixed_font"    # フォント混在
    COMPLEX = "complex"          # 複合劣化


@dataclass
class ResumeData:
    """
    履歴書に記載するデータを保持するデータクラス

    Attributes:
        name: 氏名（例: 山田太郎）
        birth_date: 生年月日（例: 1990年1月1日）
        address: 住所（例: 東京都渋谷区1-2-3）
    """

    name: str
    birth_date: str
    address: str


@dataclass
class VariationConfig:
    """
    各バリエーションの設定を保持するデータクラス

    Attributes:
        variation_type: バリエーション種別
        font_size: フォントサイズ（ポイント）
        text_color: 文字色（RGB タプル、0-255）
        rotation_angle: 回転角度（度）
        add_noise: ノイズを追加するか
        blur_radius: ぼかし半径（0で無効）
        line_thickness: 罫線の太さ（ピクセル）
        use_gothic: ゴシック体を使用するか
    """

    variation_type: VariationType
    font_size: int = 12
    text_color: tuple = (0, 0, 0)
    rotation_angle: float = 0.0
    add_noise: bool = False
    blur_radius: float = 0.0
    line_thickness: int = 1
    use_gothic: bool = False


# =============================================================================
# ダミーデータ用の名前・住所リスト
# =============================================================================
# 日本で一般的な姓
LAST_NAMES = [
    "山田", "佐藤", "鈴木", "田中", "高橋", "伊藤", "渡辺", "中村", "小林", "加藤",
    "吉田", "山本", "松本", "井上", "木村", "林", "斎藤", "清水", "山崎", "森",
]

# 男性の名前
FIRST_NAMES_MALE = [
    "太郎", "一郎", "健太", "翔太", "大輔", "直樹", "拓也", "和也", "達也", "雄太",
]

# 女性の名前
FIRST_NAMES_FEMALE = [
    "花子", "美咲", "愛", "さくら", "陽子", "真由美", "裕子", "恵子", "明美", "由美",
]

# 都道府県と市区町村のペア
PREFECTURES = [
    ("東京都", ["渋谷区", "新宿区", "港区", "千代田区", "中央区", "世田谷区", "目黒区"]),
    ("大阪府", ["大阪市北区", "大阪市中央区", "大阪市西区", "堺市", "豊中市"]),
    ("愛知県", ["名古屋市中区", "名古屋市東区", "名古屋市西区", "豊田市", "岡崎市"]),
    ("福岡県", ["福岡市博多区", "福岡市中央区", "北九州市", "久留米市"]),
    ("北海道", ["札幌市中央区", "札幌市北区", "函館市", "旭川市"]),
    ("神奈川県", ["横浜市西区", "横浜市中区", "川崎市", "相模原市"]),
    ("埼玉県", ["さいたま市大宮区", "さいたま市浦和区", "川口市", "所沢市"]),
    ("千葉県", ["千葉市中央区", "船橋市", "市川市", "柏市"]),
    ("兵庫県", ["神戸市中央区", "姫路市", "西宮市", "尼崎市"]),
    ("京都府", ["京都市中京区", "京都市下京区", "宇治市", "舞鶴市"]),
]


def generate_random_resume_data() -> ResumeData:
    """
    ランダムな履歴書データを生成する

    Returns:
        ResumeData: ランダム生成された氏名・生年月日・住所を持つデータ
    """
    # 姓をランダム選択
    last_name = random.choice(LAST_NAMES)

    # 性別をランダム決定し、対応する名前リストから選択
    is_male = random.choice([True, False])
    first_name = random.choice(FIRST_NAMES_MALE if is_male else FIRST_NAMES_FEMALE)
    name = f"{last_name}{first_name}"

    # 生年月日をランダム生成（1970年〜2000年）
    year = random.randint(1970, 2000)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # 簡略化のため28日まで
    birth_date = f"{year}年{month}月{day}日"

    # 住所をランダム生成
    prefecture, cities = random.choice(PREFECTURES)
    city = random.choice(cities)
    chome = random.randint(1, 5)
    ban = random.randint(1, 20)
    go = random.randint(1, 30)
    address = f"{prefecture}{city}{chome}-{ban}-{go}"

    return ResumeData(name=name, birth_date=birth_date, address=address)


def get_variation_config(variation_type: VariationType) -> VariationConfig:
    """
    バリエーション種別に応じた設定を取得する

    Args:
        variation_type: バリエーション種別

    Returns:
        VariationConfig: 対応する設定
    """
    configs = {
        # 標準: きれいな状態（OCR精度の基準値測定用）
        VariationType.STANDARD: VariationConfig(
            variation_type=VariationType.STANDARD,
            font_size=14,
        ),
        # 手書き風: 現状は明朝体で代用（手書きフォント導入で拡張可能）
        VariationType.HANDWRITTEN: VariationConfig(
            variation_type=VariationType.HANDWRITTEN,
            font_size=14,
        ),
        # 薄い文字: グレー色で印刷かすれを再現
        VariationType.FADED: VariationConfig(
            variation_type=VariationType.FADED,
            font_size=14,
            text_color=(150, 150, 150),  # 薄いグレー
        ),
        # 傾き: スキャン時の歪みを再現（1.5〜3度）
        VariationType.TILTED: VariationConfig(
            variation_type=VariationType.TILTED,
            font_size=14,
            rotation_angle=random.uniform(1.5, 3.0),
        ),
        # ノイズ: 紙の汚れやシミを再現
        VariationType.NOISY: VariationConfig(
            variation_type=VariationType.NOISY,
            font_size=14,
            add_noise=True,
        ),
        # ぼかし: 低解像度スキャンや手ブレを再現
        VariationType.BLURRED: VariationConfig(
            variation_type=VariationType.BLURRED,
            font_size=14,
            blur_radius=1.2,
        ),
        # 太い罫線: 罫線が文字に被って読みにくい状態を再現
        VariationType.HEAVY_LINES: VariationConfig(
            variation_type=VariationType.HEAVY_LINES,
            font_size=14,
            line_thickness=3,
        ),
        # 小さい文字: 細かい文字の認識精度を測定
        VariationType.SMALL_FONT: VariationConfig(
            variation_type=VariationType.SMALL_FONT,
            font_size=9,
        ),
        # フォント混在: 異なるフォントが混在する状況を再現
        VariationType.MIXED_FONT: VariationConfig(
            variation_type=VariationType.MIXED_FONT,
            font_size=14,
            use_gothic=True,
        ),
        # 複合劣化: 複数の劣化が重なった最悪ケース
        VariationType.COMPLEX: VariationConfig(
            variation_type=VariationType.COMPLEX,
            font_size=12,
            text_color=(120, 120, 120),  # やや薄い
            rotation_angle=random.uniform(1.0, 2.0),
            add_noise=True,
            blur_radius=0.5,
        ),
    }
    return configs[variation_type]


def create_resume_image(
    data: ResumeData,
    config: VariationConfig,
    width: int = 595,
    height: int = 842,
) -> Image.Image:
    """
    履歴書の画像を生成する

    Pillowを使用して履歴書のレイアウトを描画し、
    設定に応じて各種エフェクト（ノイズ、ぼかし、回転）を適用する。

    Args:
        data: 履歴書データ（氏名、生年月日、住所）
        config: バリエーション設定
        width: 画像の幅（ピクセル）、デフォルトはA4相当
        height: 画像の高さ（ピクセル）、デフォルトはA4相当

    Returns:
        Image.Image: 生成された履歴書画像
    """
    # 白背景の画像を作成
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # フォントの読み込み
    try:
        font_path = FONT_GOTHIC if config.use_gothic else FONT_MINCHO
        font_title = ImageFont.truetype(font_path, 24)   # タイトル用
        font_label = ImageFont.truetype(font_path, config.font_size)  # ラベル用
        font_value = ImageFont.truetype(font_path, config.font_size + 2)  # 値用
    except OSError:
        # フォントが見つからない場合はデフォルトフォントを使用
        font_title = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_value = ImageFont.load_default()

    # 罫線の設定
    line_color = (0, 0, 0)
    line_width = config.line_thickness

    # タイトル部分の描画（「履歴書」）
    draw.rectangle([40, 40, width - 40, 120], outline=line_color, width=line_width)
    draw.text((width // 2 - 50, 65), "履 歴 書", fill=config.text_color, font=font_title)

    # 入力フィールドの定義
    fields = [
        ("氏　　名", data.name),
        ("生年月日", data.birth_date),
        ("住　　所", data.address),
    ]

    # 各フィールドの描画
    y_start = 150  # 開始Y座標
    row_height = 60  # 行の高さ

    for i, (label, value) in enumerate(fields):
        y = y_start + i * row_height

        # 行の枠を描画
        draw.rectangle(
            [40, y, width - 40, y + row_height],
            outline=line_color,
            width=line_width
        )

        # ラベルと値の区切り線
        draw.line([(150, y), (150, y + row_height)], fill=line_color, width=line_width)

        # ラベルを描画
        draw.text((55, y + 18), label, fill=config.text_color, font=font_label)

        # 値を描画（フォント混在モードの場合、偶数行は明朝体を使用）
        if config.use_gothic and i % 2 == 0:
            try:
                font_value_alt = ImageFont.truetype(FONT_MINCHO, config.font_size + 2)
                draw.text((165, y + 15), value, fill=config.text_color, font=font_value_alt)
            except OSError:
                draw.text((165, y + 15), value, fill=config.text_color, font=font_value)
        else:
            draw.text((165, y + 15), value, fill=config.text_color, font=font_value)

    # エフェクトの適用（順序が重要）

    # 1. ノイズを追加
    if config.add_noise:
        img = _add_noise(img)

    # 2. ぼかしを適用
    if config.blur_radius > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=config.blur_radius))

    # 3. 回転を適用
    if config.rotation_angle != 0:
        img = img.rotate(
            config.rotation_angle,
            resample=Image.BICUBIC,
            expand=False,
            fillcolor="white",
        )

    return img


def _add_noise(img: Image.Image) -> Image.Image:
    """
    画像にノイズ（汚れ・シミ）を追加する

    紙の経年劣化や汚れを再現するため、以下を追加:
    - 小さな点（ほこりや小さな汚れ）
    - 大きな楕円（シミや水濡れ跡）

    Args:
        img: 元画像

    Returns:
        Image.Image: ノイズが追加された画像
    """
    draw = ImageDraw.Draw(img)
    width, height = img.size

    # 小さな点（ほこり・小さな汚れ）を50〜150個追加
    for _ in range(random.randint(50, 150)):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        gray = random.randint(180, 220)  # 薄いグレー
        size = random.randint(1, 3)
        draw.ellipse([x, y, x + size, y + size], fill=(gray, gray, gray))

    # 大きなシミを3〜8個追加
    for _ in range(random.randint(3, 8)):
        x = random.randint(50, width - 100)
        y = random.randint(50, height - 100)
        w = random.randint(20, 60)
        h = random.randint(10, 30)
        gray = random.randint(230, 245)  # 非常に薄いグレー
        draw.ellipse([x, y, x + w, y + h], fill=(gray, gray, gray))

    return img


def image_to_pdf(img: Image.Image, output_path: Path) -> None:
    """
    Pillow画像をPDFとして保存する

    Args:
        img: 保存する画像
        output_path: 出力先パス
    """
    pdf_buffer = BytesIO()
    img.save(pdf_buffer, format="PDF", resolution=150)
    pdf_buffer.seek(0)

    with open(output_path, "wb") as f:
        f.write(pdf_buffer.read())


def generate_all_resumes(output_dir: Path, gcs_bucket_prefix: str) -> list[dict]:
    """
    全バリエーションの履歴書PDFを生成する

    各バリエーション2個ずつ、合計20個のPDFを生成する。

    Args:
        output_dir: PDF出力先ディレクトリ
        gcs_bucket_prefix: JSONLに記載するGCSバケットのプレフィックス

    Returns:
        list[dict]: 生成されたデータセット（JSONLの内容）
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 各バリエーションを2個ずつ生成
    variations = [
        (VariationType.STANDARD, 2),
        (VariationType.HANDWRITTEN, 2),
        (VariationType.FADED, 2),
        (VariationType.TILTED, 2),
        (VariationType.NOISY, 2),
        (VariationType.BLURRED, 2),
        (VariationType.HEAVY_LINES, 2),
        (VariationType.SMALL_FONT, 2),
        (VariationType.MIXED_FONT, 2),
        (VariationType.COMPLEX, 2),
    ]

    dataset = []
    index = 1

    for variation_type, count in variations:
        for _ in range(count):
            # ランダムな履歴書データを生成
            data = generate_random_resume_data()

            # バリエーション設定を取得
            config = get_variation_config(variation_type)

            # ファイル名を決定
            filename = f"resume_{index:03d}_{variation_type.value}.pdf"
            output_path = output_dir / filename

            # 画像を生成してPDFとして保存
            img = create_resume_image(data, config)
            image_to_pdf(img, output_path)

            # 正解データ（OCRで抽出されるべきテキスト）
            target = f"氏名: {data.name}\n生年月日: {data.birth_date}\n住所: {data.address}"

            # データセットに追加
            dataset.append({
                "input_pdf": f"{gcs_bucket_prefix}/{filename}",
                "target": target,
                "variation": variation_type.value,
                "difficulty": _get_difficulty(variation_type),
            })

            print(f"Generated: {filename}")
            index += 1

    return dataset


def _get_difficulty(variation_type: VariationType) -> str:
    """
    バリエーション種別からOCR難易度を取得する

    Args:
        variation_type: バリエーション種別

    Returns:
        str: 難易度（"easy", "medium", "hard"）
    """
    difficulty_map = {
        VariationType.STANDARD: "easy",
        VariationType.HANDWRITTEN: "medium",
        VariationType.FADED: "medium",
        VariationType.TILTED: "medium",
        VariationType.NOISY: "hard",
        VariationType.BLURRED: "hard",
        VariationType.HEAVY_LINES: "medium",
        VariationType.SMALL_FONT: "medium",
        VariationType.MIXED_FONT: "medium",
        VariationType.COMPLEX: "hard",
    }
    return difficulty_map[variation_type]


def save_jsonl(dataset: list[dict], output_path: Path) -> None:
    """
    データセットをJSONL形式で保存する

    Args:
        dataset: 保存するデータセット
        output_path: 出力先パス
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Saved: {output_path}")


def main() -> None:
    """
    メイン処理

    1. 全バリエーションのPDFを生成
    2. データセット（JSONL）を保存
    """
    # GCSバケットのプレフィックス（実際の環境に合わせて変更すること）
    gcs_bucket_prefix = "gs://your-bucket/resumes"

    # PDF生成
    dataset = generate_all_resumes(OUTPUT_DIR, gcs_bucket_prefix)

    # JSONL保存
    save_jsonl(dataset, JSONL_PATH)

    # 完了メッセージ
    print(f"\nGenerated {len(dataset)} PDFs")
    print(f"JSONL saved to: {JSONL_PATH}")


if __name__ == "__main__":
    main()