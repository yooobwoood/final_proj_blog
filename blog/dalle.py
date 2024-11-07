from openai import OpenAI, BadRequestError
import requests
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
import os
import base64
import datetime
from django.conf import settings
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_KEY")
def save_gen_img(client, txt_response: str):
    img_response = client.images.generate(
        model="dall-e-3",
        prompt=f"{txt_response}, in style of vector art, square aspect ratio",
        size="1024x1024",
        quality="standard",
        response_format="b64_json",
        n=1,
    )
    image_data_b64 = img_response.data[0].b64_json
    image_bytes = base64.b64decode(image_data_b64)
    # 저장 경로와 파일명 설정
    gentime_info = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{gentime_info}.png"
    file_path = os.path.join(settings.MEDIA_ROOT, 'generated_images', filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'wb') as img_file:
        img_file.write(image_bytes)
    return filename