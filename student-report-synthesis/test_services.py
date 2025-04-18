import requests
import openai
import os

# === CONFIG ===
FORM_RECOGNIZER_ENDPOINT = os.getenv("FORM_RECOGNIZER_ENDPOINT", "https://<your-form-recognizer-endpoint>.cognitiveservices.azure.com/")
FORM_RECOGNIZER_KEY = os.getenv("FORM_RECOGNIZER_KEY", "<your-form-recognizer-key>")

OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT", "https://api.openai.com/v1/chat/completions")
OPENAI_KEY = os.getenv("OPENAI_KEY", "<your-openai-key>")

# === Test Form Recognizer ===
def test_form_recognizer():
    url = f"{FORM_RECOGNIZER_ENDPOINT}formrecognizer/documentModels/prebuilt-layout:analyze?api-version=2023-07-31"
    headers = {
        "Ocp-Apim-Subscription-Key": FORM_RECOGNIZER_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "urlSource": "https://aka.ms/azsdk/formrecognizer/sampledocument"  # public test PDF
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code in [200, 202]:
            print("✅ Form Recognizer API key and endpoint are working.")
        else:
            print(f"❌ Form Recognizer failed: {response.status_code} {response.text}")
    except Exception as e:
        print(f"❌ Exception testing Form Recognizer: {e}")

# === Test OpenAI ===
def test_openai():
    try:
        openai.api_key = OPENAI_KEY
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.0,
            max_tokens=10
        )
        print("✅ OpenAI API key is working.")
    except Exception as e:
        print(f"❌ Failed to connect to OpenAI API: {e}")

# === Run Tests ===
if __name__ == "__main__":
    print("🔍 Testing Azure Form Recognizer...")
    test_form_recognizer()
    print("🔍 Testing OpenAI API...")
    test_openai()
