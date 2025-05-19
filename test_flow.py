from r2r import R2RAsyncClient
import asyncio

async def cleanup_resources(client):
    """Clean up existing documents and collections"""
    try:
        # List and cleanup existing collections
        collections = await client.collections.list()
        if collections and 'results' in collections:
            for collection in collections['results']:
                try:
                    await client.collections.delete(id=collection['id'])
                    print(f"Cleaned up collection: {collection['id']}")
                except Exception as e:
                    print(f"Error cleaning up collection {collection['id']}: {e}")

        # List and cleanup existing documents
        documents = await client.documents.list()
        if documents and 'results' in documents:
            for doc in documents['results']:
                try:
                    await client.documents.delete(id=doc['id'])
                    print(f"Cleaned up document: {doc['id']}")
                except Exception as e:
                    print(f"Error cleaning up document {doc['id']}: {e}")
                    
        print("✓ Cleanup completed")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")

async def test_basic_workflow():
    """Test basic R2R functionality with a simple medical text"""
    client = R2RAsyncClient("http://jovana.openbrain.io:7272")
    
    try:
        # Cleanup existing resources first
        print("Cleaning up existing resources...")
        await cleanup_resources(client)
        
        # Create a simple test document
        print("\nCreating test document...")
        doc_response = await client.documents.create(
            raw_text="""
            Hypertension treatment often includes ACE inhibitors like lisinopril.
            These medications work by blocking the conversion of angiotensin I to
            angiotensin II, thereby reducing blood pressure. Common side effects
            include dry cough and dizziness. Studies show a 10-15mmHg reduction
            in systolic blood pressure for most patients.
            """,
            metadata={
                "title": "Hypertension Treatment Overview",
                "type": "medical_summary"
            }
        )
        
        doc_id = doc_response['results']['document_id']
        print(f"✓ Document created with ID: {doc_id}")
        
        # Create a collection with unique name
        print("\nCreating collection...")
        collection_response = await client.collections.create(
            name=f"Medical Literature {asyncio.get_event_loop().time()}",  # Ensure unique name
            description="Collection of medical papers and summaries"
        )
        collection_id = collection_response['results']['id']
        print(f"✓ Collection created with ID: {collection_id}")
        
        # Add document to collection
        print("\nAdding document to collection...")
        await client.collections.add_document(
            id=collection_id,
            document_id=doc_id
        )
        print("✓ Document added to collection")
        
        # Wait a moment for indexing
        print("\nWaiting for indexing...")
        await asyncio.sleep(5)
        
        # Test search functionality
        print("\nTesting search...")
        search_result = await client.retrieval.search(
            query="What are the side effects of ACE inhibitors?"
        )
        print("✓ Search successful")
        
        if search_result and 'results' in search_result:
            chunks = search_result['results'].get('chunkSearchResults', [])
            print(f"\nFound {len(chunks)} relevant chunks")
            for i, chunk in enumerate(chunks, 1):
                print(f"\nChunk {i}:")
                print(f"Text: {chunk.get('text', '')[:200]}...")
                print(f"Score: {chunk.get('score', 'N/A')}")
        
        print("\nAll basic functionality tests passed!")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_basic_workflow())