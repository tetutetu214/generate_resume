"""
履歴書PDF生成器 - AIOCR テスト素材用
各種バリエーション（ノイズ、ぼかし、傾き等）のPDFを生成
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


FONT_MINCHO = "/usr/share/fonts/opentype/ipaexfont-mincho/ipaexm.ttf"
FONT_GOTHIC = "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf"

OUTPUT_DIR = Path("outputs/pdfs")
JSONL_PATH = Path("outputs/dataset.jsonl")


class VariationType(Enum):
    STANDARD = "standard"
    HANDWRITTEN = "handwritten"
    FADED = "faded"
    TILTED = "tilted"
    NOISY = "noisy"
    BLURRED = "blurred"
    HEAVY_LINES = "heavy_lines"
    SMALL_FONT = "small_font"
    MIXED_FONT = "mixed_font"
    COMPLEX = "complex"


@dataclass
class ResumeData:
    name: str
    birth_date: str
    address: str


@dataclass
class VariationConfig:
    variation_type: VariationType
    font_size: int = 12
    text_color: tuple = (0, 0, 0)
    rotation_angle: float = 0.0
    add_noise: bool = False
    blur_radius: float = 0.0
    line_thickness: int = 1
    use_gothic: bool = False


LAST_NAMES = [
    "山田", "佐藤", "鈴木", "田中", "高橋", "伊藤", "渡辺", "中村", "小林", "加藤",
    "吉田", "山本", "松本", "井上", "木村", "林", "斎藤", "清水", "山崎", "森",
]

FIRST_NAMES_MALE = [
    "太郎", "一郎", "健太", "翔太", "大輔", "直樹", "拓也", "和也", "達也", "雄太",
]

FIRST_NAMES_FEMALE = [
    "花子", "美咲", "愛", "さくら", "陽子", "真由美", "裕子", "恵子", "明美", "由美",
]

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


def generate_random_resume_data() -> ResumeData:a
    last_name = random.choice(LAST_NAMES)
    is_male = random.choice([True, False])
    first_name = random.choice(FIRST_NAMES_MALE if is_male else FIRST_NAMES_FEMALE)
    name = f"{last_name}{first_name}"

    year = random.randint(1970, 2000)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    birth_date = f"{year}年{month}月{day}日"

    prefecture, cities = random.choice(PREFECTURES)
    city = random.choice(cities)
    chome = random.randint(1, 5)
    ban = random.randint(1, 20)
    go = random.randint(1, 30)
    address = f"{prefecture}{city}{chome}-{ban}-{go}"

    return ResumeData(name=name, birth_date=birth_date, address=address)


def get_variation_config(variation_type: VariationType) -> VariationConfig:
    configs = {
        VariationType.STANDARD: VariationConfig(
            variation_type=VariationType.STANDARD,
            font_size=14,
        ),
        VariationType.HANDWRITTEN: VariationConfig(
            variation_type=VariationType.HANDWRITTEN,
            font_size=14,
        ),
        VariationType.FADED: VariationConfig(
            variation_type=VariationType.FADED,
            font_size=14,
            text_color=(150, 150, 150),
        ),
        VariationType.TILTED: VariationConfig(
            variation_type=VariationType.TILTED,
            font_size=14,
            rotation_angle=random.uniform(1.5, 3.0),
        ),
        VariationType.NOISY: VariationConfig(
            variation_type=VariationType.NOISY,
            font_size=14,
            add_noise=True,
        ),
        VariationType.BLURRED: VariationConfig(
            variation_type=VariationType.BLURRED,
            font_size=14,
            blur_radius=1.2,
        ),
        VariationType.HEAVY_LINES: VariationConfig(
            variation_type=VariationType.HEAVY_LINES,
            font_size=14,
            line_thickness=3,
        ),
        VariationType.SMALL_FONT: VariationConfig(
            variation_type=VariationType.SMALL_FONT,
            font_size=9,
        ),
        VariationType.MIXED_FONT: VariationConfig(
            variation_type=VariationType.MIXED_FONT,
            font_size=14,
            use_gothic=True,
        ),
        VariationType.COMPLEX: VariationConfig(
            variation_type=VariationType.COMPLEX,
            font_size=12,
            text_color=(120, 120, 120),
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
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    try:
        font_path = FONT_GOTHIC if config.use_gothic else FONT_MINCHO
        font_title = ImageFont.truetype(font_path, 24)
        font_label = ImageFont.truetype(font_path, config.font_size)
        font_value = ImageFont.truetype(font_path, config.font_size + 2)
    except OSError:
        font_title = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_value = ImageFont.load_default()

    line_color = (0, 0, 0)
    line_width = config.line_thickness

    draw.rectangle([40, 40, width - 40, 120], outline=line_color, width=line_width)
    draw.text((width // 2 - 50, 65), "履 歴 書", fill=config.text_color, font=font_title)

    fields = [
        ("氏　　名", data.name),
        ("生年月日", data.birth_date),
        ("住　　所", data.address),
    ]

    y_start = 150
    row_height = 60

    for i, (label, value) in enumerate(fields):
        y = y_start + i * row_height
        draw.rectangle([40, y, width - 40, y + row_height], outline=line_color, width=line_width)
        draw.line([(150, y), (150, y + row_height)], fill=line_color, width=line_width)
        draw.text((55, y + 18), label, fill=config.text_color, font=font_label)

        if config.use_gothic and i % 2 == 0:
            try:
                font_value_alt = ImageFont.truetype(FONT_MINCHO, config.font_size + 2)
                draw.text((165, y + 15), value, fill=config.text_color, font=font_value_alt)
            except OSError:
                draw.text((165, y + 15), value, fill=config.text_color, font=font_value)
        else:
            draw.text((165, y + 15), value, fill=config.text_color, font=font_value)

    if config.add_noise:
        img = _add_noise(img)

    if config.blur_radius > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=config.blur_radius))

    if config.rotation_angle != 0:
        img = img.rotate(
            config.rotation_angle,
            resample=Image.BICUBIC,
            expand=False,
            fillcolor="white",
        )

    return img


def _add_noise(img: Image.Image) -> Image.Image:
    draw = ImageDraw.Draw(img)
    width, height = img.size

    for _ in range(random.randint(50, 150)):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        gray = random.randint(180, 220)
        size = random.randint(1, 3)
        draw.ellipse([x, y, x + size, y + size], fill=(gray, gray, gray))

    for _ in range(random.randint(3, 8)):
        x = random.randint(50, width - 100)
        y = random.randint(50, height - 100)
        w = random.randint(20, 60)
        h = random.randint(10, 30)
        gray = random.randint(230, 245)
        draw.ellipse([x, y, x + w, y + h], fill=(gray, gray, gray))

    return img


def image_to_pdf(img: Image.Image, output_path: Path) -> None:
    pdf_buffer = BytesIO()
    img.save(pdf_buffer, format="PDF", resolution=150)
    pdf_buffer.seek(0)

    with open(output_path, "wb") as f:
        f.write(pdf_buffer.read())


def generate_all_resumes(output_dir: Path, gcs_bucket_prefix: str) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)

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
            data = generate_random_resume_data()
            config = get_variation_config(variation_type)

            filename = f"resume_{index:03d}_{variation_type.value}.pdf"
            output_path = output_dir / filename

            img = create_resume_image(data, config)
            image_to_pdf(img, output_path)

            target = f"氏名: {data.name}\n生年月日: {data.birth_date}\n住所: {data.address}"

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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Saved: {output_path}")


def main() -> None:
    gcs_bucket_prefix = "gs://your-bucket/resumes"

    dataset = generate_all_resumes(OUTPUT_DIR, gcs_bucket_prefix)
    save_jsonl(dataset, JSONL_PATH)

    print(f"\nGenerated {len(dataset)} PDFs")
    print(f"JSONL saved to: {JSONL_PATH}")


if __name__ == "__main__":
    main()
