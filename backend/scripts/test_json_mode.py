import sys
import os
from dotenv import load_dotenv
load_dotenv('D:/Bizpulse/backend/.env')
from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
model = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')
cfg = types.GenerateContentConfig(response_mime_type='application/json')
resp = client.models.generate_content(
    model=model,
    contents='Output a JSON object with key status and value ok',
    config=cfg
)
print('JSON Mode Output:', resp.text)
