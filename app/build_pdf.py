import io

import pymupdf
from PIL import Image

PX_TO_PT = 0.75


def build_pdf(slides, output_path, scale=1):
    doc = pymupdf.open()
    for slide in slides:
        width_px, height_px = Image.open(io.BytesIO(slide["png"])).size
        page = doc.new_page(width=width_px / scale * PX_TO_PT, height=height_px / scale * PX_TO_PT)
        page.insert_image(page.rect, stream=slide["png"])

    doc.save(output_path, deflate=True)
    doc.close()
