
import base64
import io

from pathlib import Path
from functools import lru_cache
from PIL import Image, ImageOps, ImageChops


# ============================================================
# 1. 이미지 마스크 변환
# ============================================================

@lru_cache(maxsize=32)
def make_image_mask(path, is_map=False):
    """
    이미지를 CSS 마스크용 Base64 문자열로 변환.

    is_map=True:
        세계지도 전용 처리 + 양옆 그라데이션

    is_map=False:
        검은 아이콘 / 흰 배경 기준 투명 마스크
    """

    image = Image.open(path).convert("RGBA")
    gray = ImageOps.grayscale(image.convert("RGB"))

    if is_map:
        # 흰 배경은 투명하게, 회색 지도만 남기기
        alpha = gray.point(
            lambda p: max(0, min(255, (250 - p) * 8))
        )

        # 양옆 경계를 부드럽게 처리
        width, height = image.size
        fade_width = max(1, int(width * 0.15))

        gradient = Image.new("L", (width, 1))

        gradient.putdata([
            int(255 * min(
                1,
                x / fade_width,
                (width - 1 - x) / fade_width
            ))
            for x in range(width)
        ])

        gradient = gradient.resize((width, height))
        alpha = ImageChops.multiply(alpha, gradient)

    else:
        # 검은 아이콘은 남기고 흰 배경은 투명하게
        alpha = ImageOps.invert(gray)

    # 원본 이미지의 투명도 반영
    alpha = ImageChops.multiply(
        alpha,
        image.getchannel("A")
    )

    # 투명 마스크 이미지 생성
    mask = Image.new(
        "RGBA",
        image.size,
        (255, 255, 255, 0)
    )

    mask.putalpha(alpha)

    # PNG 이미지를 메모리에 저장
    buffer = io.BytesIO()
    mask.save(buffer, format="PNG")

    # Base64 문자열로 변환
    return base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")


# ============================================================
# 2. 테마 자동 대응 아이콘 HTML 생성
# ============================================================

def mask_icon_html(path, size=24):
    """
    PNG 아이콘을 라이트/다크 모드에 대응하는
    HTML 아이콘으로 변환.

    path: 아이콘 이미지 경로
    size: 아이콘 크기(px)
    """

    # 이미지가 없으면 빈 문자열 반환
    path = Path(path)

    if not path.is_file():
        return ""

    icon_base64 = make_image_mask(path)

    return f"""
    <span style="
        display:inline-block;
        width:{int(size)}px;
        height:{int(size)}px;
        flex-shrink:0;

        background-color:currentColor;

        -webkit-mask:
            url('data:image/png;base64,{icon_base64}')
            center / contain no-repeat;

        mask:
            url('data:image/png;base64,{icon_base64}')
            center / contain no-repeat;
    "></span>
    """
