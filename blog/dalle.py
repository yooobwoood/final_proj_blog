from openai import OpenAI, BadRequestError
import requests
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
import os
import base64
import datetime
from django.conf import settings
import io

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_KEY")

def resize_to_half_height(image_bytes: bytes) -> bytes:
    # BytesIO를 사용하여 bytes 데이터를 Pillow 이미지 객체로 변환
    with io.BytesIO(image_bytes) as input_buffer:
        with Image.open(input_buffer) as img:
            # 이미지의 현재 너비와 높이 얻기
            original_width, original_height = img.size
            # 목표 비율 설정 (2:1) - 가로가 세로의 두 배
            target_width = original_width
            target_height = original_width // 2
            # 이미지 크롭 또는 패딩이 필요할 경우 설정
            if original_height > target_height:
                # 세로가 더 긴 경우, 위아래를 잘라냄
                top = (original_height - target_height) // 2
                bottom = top + target_height
                img_cropped = img.crop((0, top, target_width, bottom))
            else:
                # 세로가 부족한 경우, 빈 공간을 추가할 수도 있음 (여기서는 크롭만 구현)
                img_cropped = img
            # 결과 이미지를 BytesIO로 다시 저장
            with io.BytesIO() as output_buffer:
                img_cropped.save(output_buffer, format="PNG")
                resized_image_bytes = output_buffer.getvalue()
    return resized_image_bytes

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
    _image_bytes = base64.b64decode(image_data_b64)
    image_bytes = resize_to_half_height(_image_bytes)
    
    # 저장 경로와 파일명 설정
    gentime_info = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{gentime_info}.png"
    folder_path = os.path.join(settings.MEDIA_ROOT, 'generated_images')
    file_path = os.path.join(folder_path, filename)

    os.makedirs(folder_path, exist_ok=True)

    with open(file_path, 'wb') as img_file:
        img_file.write(image_bytes)
    return filename