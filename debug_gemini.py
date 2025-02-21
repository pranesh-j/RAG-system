import google.generativeai as genai
from app.core.config import settings

def test_gemini_api():
    """Test script to verify Gemini API functionality"""
    try:
        # Configure the API
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        
        # Print available models
        print("Available Models:")
        for m in genai.list_models():
            print(f"- {m.name}: {m.supported_generation_methods}")
            
        # Try to get embeddings
        model = genai.GenerativeModel('embedding-001')
        print("\nModel methods:", dir(model))
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_gemini_api()