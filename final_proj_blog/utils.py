import pickle
import torch
from django.conf import settings
import boto3

def download_index_from_s3(file_name, local_path):
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    s3.download_file(bucket_name, file_name, local_path)



# Custom unpickler to recognize custom tokenizers
class CustomUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if name == 'kkma_tokenize':
            from today_word.words700 import kkma_tokenize  
            return kkma_tokenize
        if name == 'okt_tokenize':
            from blog.easystory import okt_tokenize  
            return okt_tokenize
        return super().find_class(module, name)
    

def load_index(local_path):
    with open(local_path, 'rb') as f:
        try:
            index = CustomUnpickler(f).load()
        except Exception:
            f.seek(0)
            index = torch.load(f, map_location="cpu")
    return index