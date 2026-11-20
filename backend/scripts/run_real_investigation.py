import sys
import os
import json
import time

sys.path.insert(0, 'D:/Bizpulse/backend')
from dotenv import load_dotenv
load_dotenv('D:/Bizpulse/backend/.env')

from app.services.investigation_service import run_mobile_payment_investigation

def main():
    print("=" * 70)
    print("BIZPULSE - LIVE BUSINESS INVESTIGATION (GEMINI + PYTHON ENGINE)")
    print("=" * 70)
    print("Extracting verified metrics from CSVs and dispatching to Gemini...")
    
    t0 = time.time()
    investigation = run_mobile_payment_investigation()
    elapsed = round(time.time() - t0, 2)
    
    print(f"Investigation completed in {elapsed}s!")
    print("\n" + "=" * 70)
    print(json.dumps(investigation.model_dump(), indent=2))
    print("=" * 70)

if __name__ == '__main__':
    main()
