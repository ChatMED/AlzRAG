from r2r import R2RAsyncClient
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

async def cleanup_all_resources():
    """Clean up all collections and documents in R2R"""
    client = R2RAsyncClient("http://jovana.openbrain.io:7272")
    
    try:
        # First list and delete all collections
        logger.info("Listing collections...")
        collections = await client.collections.list()
        if collections and 'results' in collections:
            for collection in collections['results']:
                try:
                    await client.collections.delete(id=collection['id'])
                    logger.info(f"Deleted collection: {collection['id']} ({collection.get('name', 'unnamed')})")
                except Exception as e:
                    logger.error(f"Failed to delete collection {collection['id']}: {e}")

        # Then list and delete all documents
        logger.info("\nListing documents...")
        documents = await client.documents.list()
        if documents and 'results' in documents:
            for doc in documents['results']:
                try:
                    await client.documents.delete(id=doc['id'])
                    logger.info(f"Deleted document: {doc['id']} ({doc.get('metadata', {}).get('title', 'untitled')})")
                except Exception as e:
                    logger.error(f"Failed to delete document {doc['id']}: {e}")

        logger.info("\nCleanup completed!")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    asyncio.run(cleanup_all_resources())