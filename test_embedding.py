from app.services.embeddings import embedding_service
import asyncio

async def test_embedding():
    try:
        text = "This is a test document"
        embedding = await embedding_service.get_embeddings(text)
        print(f"Successfully generated embedding of length: {len(embedding)}")
        print(f"First few values: {embedding[:5]}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_embedding())