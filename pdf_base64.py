# write code to extract pdf pages in high resolution image and save it as a base64 string

import PyPDF2
import io
import base64
import pypdfium2

def pdf_to_base64(pdf_path):
    with open(pdf_path, "rb") as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page in pdf_reader.pages:
            # Convert page to image using pypdfium2 instead since PyPDF2 doesn't have image conversion
            pdf = pypdfium2.PdfDocument(pdf_path)
            page_obj = pdf[page.page_number]
            bitmap = page_obj.render(scale=2.0)  # Scale 2.0 gives good resolution
            image = bitmap.to_pil()
            image.save("page.png")

    with open("page.png", "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


print(pdf_to_base64("test.pdf"))
