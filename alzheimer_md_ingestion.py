import logging
import os
import uuid
import asyncio
import aiohttp
import json
import random
from r2r import R2RAsyncClient
from typing import List, Dict, Optional, Any, Set
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import quote_plus
import ssl
import re
from datetime import datetime, timedelta
import pickle

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class MedicalKGPipeline:
    # UMLS API endpoints
    UMLS_AUTH_ENDPOINT = "https://utslogin.nlm.nih.gov/cas/v1/api-key"
    UMLS_SEARCH_ENDPOINT = "https://uts-ws.nlm.nih.gov/rest/search/current"
    UMLS_CONTENT_ENDPOINT = "https://uts-ws.nlm.nih.gov/rest/content/current"
    
    def __init__(self, base_url="http://jovana.openbrain.io:7272", umls_api_key=None, 
                 max_retries=3, retry_delay=10, persistence_file="pipeline_state.pkl"):
        """
        Initialize the pipeline with R2R client and UMLS credentials
        
        Args:
            base_url: The R2R server URL
            umls_api_key: API key for UMLS access
            max_retries: Maximum number of retries for failed API calls
            retry_delay: Base delay between retries in seconds
            persistence_file: File to store progress information
        """
        self.client = R2RAsyncClient(base_url=base_url)
        self.umls_api_key = umls_api_key or "cb3ce71e-bf6d-4444-ab14-faf48d1bf86f"
        self.umls_token = None
        self.umls_tgt_url = None
        
        # SSL context for UMLS API calls
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # Retry configuration
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # State persistence
        self.persistence_file = persistence_file
        self.state = self._load_state() or {
            "ingested_docs": set(),
            "entity_extracted_docs": set(),
            "relationship_extracted_docs": set(),
            "collection_id": None
        }
        
        logger.info(f"Initialized MedicalKGPipeline with base_url={base_url}, max_retries={max_retries}")

    def _load_state(self):
        """Load pipeline state from disk"""
        try:
            if os.path.exists(self.persistence_file):
                with open(self.persistence_file, 'rb') as f:
                    state = pickle.load(f)
                logger.info(f"Loaded pipeline state from {self.persistence_file}")
                return state
            return None
        except Exception as e:
            logger.error(f"Failed to load pipeline state: {e}")
            return None
    
    def _save_state(self):
        """Save pipeline state to disk"""
        try:
            with open(self.persistence_file, 'wb') as f:
                pickle.dump(self.state, f)
            logger.debug(f"Saved pipeline state to {self.persistence_file}")
        except Exception as e:
            logger.error(f"Failed to save pipeline state: {e}")

    MEDICAL_ENTITY_PROMPT = """
    Extract medical entities from the text. For each entity:
    1. Name: The exact medical term as it appears
    2. Type: Categorize as one of:
       - Disease/Condition
       - Medication/Drug
       - Procedure
       - Symptom
       - Laboratory Test
       - Anatomical Structure
       - Physiological Function
    3. Context: The relevant sentence or phrase
    4. Attributes: Any quantitative measures, dosages, or specific details

    Focus on precision and maintain medical terminology.
    If the same concept appears with different names, note all variations.
    """

    MEDICAL_RELATIONSHIP_PROMPT = """
    Analyze the medical text and extract relationships between entities. For each relationship:
    1. Source Entity: The starting point entity
    2. Relationship Type: One of:
       - treats (medication → condition)
       - causes (factor → outcome)
       - diagnoses (test → condition)
       - indicates (symptom → condition)
       - part_of (structure → system)
       - measures (test → parameter)
    3. Target Entity: The endpoint entity
    4. Evidence: Supporting text or statistical measures
    5. Confidence: High/Medium/Low based on the evidence

    Include any statistical significance (p-values) or confidence intervals if present.
    """

    async def retry_api_call(self, func, *args, **kwargs):
        """Retry API calls with exponential backoff"""
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                if retry_count > 0:
                    delay = self.retry_delay * (2 ** (retry_count - 1)) + random.uniform(1.0, 5.0)
                    logger.warning(f"Retry {retry_count}/{self.max_retries}: waiting {delay:.2f}s")
                    await asyncio.sleep(delay)
                
                # Make the API call
                result = await func(*args, **kwargs)
                return result
                
            except Exception as e:
                last_error = e
                retry_count += 1
                error_msg = str(e).strip()
                
                # Check if this is a rate limit error
                if "429" in error_msg or "too many requests" in error_msg.lower():
                    logger.warning(f"Rate limit exceeded, will retry ({retry_count}/{self.max_retries})")
                    # For rate limit errors, increase the delay significantly
                    await asyncio.sleep(self.retry_delay * 2 * retry_count)
                else:
                    logger.warning(f"API call failed: {error_msg}, will retry ({retry_count}/{self.max_retries})")
        
        # If we get here, all retries failed
        logger.error(f"Maximum retries ({self.max_retries}) exceeded: {last_error}")
        raise last_error
    async def create_mri_collection(self, name: str, description: str = "") -> str:
        """
        Create a new collection specifically for MRI images and their descriptions
        
        Args:
            name: Name of the collection
            description: Optional description for the collection
                
        Returns:
            str: Collection ID
        """
        try:
            # Create a new collection for MRI data
            response = await self.retry_api_call(
                self.client.collections.create,
                name=name,
                description=description or "Collection of MRI images and their clinical descriptions"
            )
            
            collection_id = response['results']['id']
            logger.info(f"✓ Created new MRI collection {name} with ID {collection_id}")
                        
            # Save the collection ID in our state
            self.state["mri_collection_id"] = collection_id
            self._save_state()
                        
            return collection_id
            
        except Exception as e:
            logger.error(f"✗ Failed to create MRI collection: {e}")
            return None
    async def get_umls_token(self):
        """Get authentication token for UMLS API with proper two-step authentication flow"""
        if not self.umls_api_key:
            raise ValueError("UMLS API key not provided in environment variables")
            
        try:
            # Step 1: Request a TGT (Ticket Granting Ticket)
            auth_data = {
                'apikey': self.umls_api_key
            }
            
            # Create SSL context that ignores certificate verification
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            conn = aiohttp.TCPConnector(ssl=ssl_context)
            
            async with aiohttp.ClientSession(connector=conn) as session:
                # First step: Get the TGT
                async with session.post(self.UMLS_AUTH_ENDPOINT, data=auth_data) as response:
                    if response.status != 201:  # TGT creation returns 201 Created
                        raise Exception(f"UMLS TGT creation failed: {await response.text()}")
                    
                    # Extract the TGT URL from the response
                    response_text = await response.text()
                    tgt_pattern = r'action="(https://utslogin\.nlm\.nih\.gov/cas/v1/api-key/TGT-[^"]+)"'
                    tgt_match = re.search(tgt_pattern, response_text)
                    
                    if not tgt_match:
                        raise Exception("Failed to extract TGT URL from UMLS response")
                    
                    tgt_url = tgt_match.group(1)
                    logger.debug(f"Obtained TGT URL: {tgt_url}")
                    
                    # Step 2: Use the TGT to get a service ticket
                    service_data = {
                        'service': 'http://umlsks.nlm.nih.gov'
                    }
                    
                    async with session.post(tgt_url, data=service_data) as ticket_response:
                        if ticket_response.status != 200:
                            raise Exception(f"UMLS service ticket request failed: {await ticket_response.text()}")
                        
                        # The response body is the service ticket
                        self.umls_token = await ticket_response.text()
                        
                        if not self.umls_token:
                            raise ValueError("Failed to obtain UMLS service ticket")
                        
                        logger.info("✓ Obtained UMLS service ticket")
                        return self.umls_token
        except Exception as e:
            logger.error(f"✗ Error getting UMLS token: {e}")
            raise

    async def get_umls_service_ticket(self):
        """Get a fresh service ticket from UMLS using the TGT"""
        if not hasattr(self, 'umls_tgt_url') or not self.umls_tgt_url:
            # Get a new TGT first
            await self.get_umls_tgt()
            
        try:
            # Create SSL context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            conn = aiohttp.TCPConnector(ssl=ssl_context)
            
            # Step 2: Use the TGT to get a fresh service ticket
            service_data = {
                'service': 'http://umlsks.nlm.nih.gov'
            }
            
            async with aiohttp.ClientSession(connector=conn) as session:
                async with session.post(self.umls_tgt_url, data=service_data) as ticket_response:
                    if ticket_response.status != 200:
                        raise Exception(f"UMLS service ticket request failed: {await ticket_response.text()}")
                    
                    # The response body is the service ticket
                    service_ticket = await ticket_response.text()
                    
                    if not service_ticket:
                        raise ValueError("Failed to obtain UMLS service ticket")
                    
                    logger.debug("✓ Obtained fresh UMLS service ticket")
                    return service_ticket
        except Exception as e:
            logger.error(f"✗ Error getting UMLS service ticket: {e}")
            # If we get an error, the TGT might be expired, try to get a new one
            try:
                await self.get_umls_tgt()
                return await self.get_umls_service_ticket()
            except Exception as refresh_error:
                logger.error(f"✗ Failed to refresh UMLS TGT: {refresh_error}")
                raise

    async def get_umls_tgt(self):
        """Get a TGT (Ticket Granting Ticket) from UMLS"""
        if not self.umls_api_key:
            raise ValueError("UMLS API key not provided in environment variables")
            
        try:
            # Step 1: Request a TGT (Ticket Granting Ticket)
            auth_data = {
                'apikey': self.umls_api_key
            }
            
            # Create SSL context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            conn = aiohttp.TCPConnector(ssl=ssl_context)
            
            async with aiohttp.ClientSession(connector=conn) as session:
                # First step: Get the TGT
                async with session.post(self.UMLS_AUTH_ENDPOINT, data=auth_data) as response:
                    if response.status != 201:  # TGT creation returns 201 Created
                        raise Exception(f"UMLS TGT creation failed: {await response.text()}")
                    
                    # Extract the TGT URL from the response
                    response_text = await response.text()
                    tgt_pattern = r'action="(https://utslogin\.nlm\.nih\.gov/cas/v1/api-key/TGT-[^"]+)"'
                    tgt_match = re.search(tgt_pattern, response_text)
                    
                    if not tgt_match:
                        raise Exception("Failed to extract TGT URL from UMLS response")
                    
                    self.umls_tgt_url = tgt_match.group(1)
                    logger.info(f"✓ Obtained new UMLS TGT")
                    return self.umls_tgt_url
        except Exception as e:
            logger.error(f"✗ Error getting UMLS TGT: {e}")
            raise

    async def search_umls(self, term: str) -> Optional[Dict[str, Any]]:
        """Search UMLS for a medical term and return best matching concept"""
        try:
            service_ticket = await self.get_umls_service_ticket()
                
            # URL encode the term
            encoded_term = quote_plus(term)
            
            params = {
                'string': term,
                'ticket': service_ticket,  # Fresh service ticket
                'searchType': 'exact',
                'returnIdType': 'code',
                'sabs': 'SNOMEDCT_US,ICD10CM,RXNORM,MSH',
                'pageSize': 5
            }
        
            # Create SSL context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            conn = aiohttp.TCPConnector(ssl=ssl_context)
                    
            async with aiohttp.ClientSession(connector=conn) as session:
                async with session.get(self.UMLS_SEARCH_ENDPOINT, params=params) as response:
                    if response.status != 200:
                        logger.warning(f"UMLS search failed: {await response.text()}")
                        return None
                        
                    data = await response.json()
                    results = data.get('result', {}).get('results', [])
                    
                    # If no exact match, try word match
                    if not results:
                        params['searchType'] = 'words'
                        async with session.get(self.UMLS_SEARCH_ENDPOINT, params=params) as word_response:
                            if word_response.status != 200:
                                return None
                                
                            word_data = await word_response.json()
                            results = word_data.get('result', {}).get('results', [])
                    
                    # If still no results, return None
                    if not results:
                        logger.debug(f"No UMLS concepts found for: {term}")
                        return None
                    
                    # Get the best match
                    best_match = results[0]
                    cui = best_match.get('ui')
                    
                    if cui:
                        # Get additional details
                        concept_details = await self._get_umls_concept_details(cui)
                        
                        return {
                            'cui': cui,
                            'name': best_match.get('name'),
                            'preferred_term': concept_details.get('preferred_term') or best_match.get('name'),
                            'semantic_types': concept_details.get('semantic_types', []),
                            'definitions': concept_details.get('definitions', []),
                            'synonyms': concept_details.get('synonyms', []),
                            'parents': concept_details.get('parents', []),
                            'children': concept_details.get('children', [])
                        }
                        
                    return None
                    
        except Exception as e:
            logger.error(f"✗ Error searching UMLS for '{term}': {e}")
            return None

    async def _get_umls_concept_details(self, cui: str) -> Dict[str, Any]:
        """Get detailed information about a UMLS concept with SSL handling"""
        if not self.umls_token:
            await self.get_umls_token()
            
        result = {
            'preferred_term': None,
            'semantic_types': [],
            'definitions': [],
            'synonyms': [],
            'parents': [],
            'children': []
        }
        
        try:
            params = {'ticket': self.umls_token}
            
            # Base concept endpoint
            concept_endpoint = f"{self.UMLS_CONTENT_ENDPOINT}/CUI/{cui}"
            
            # Create connector with our SSL context
            conn = aiohttp.TCPConnector(ssl=self.ssl_context)
            
            async with aiohttp.ClientSession(connector=conn) as session:
                # Get basic concept info
                async with session.get(concept_endpoint, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        result['preferred_term'] = data.get('result', {}).get('name')
                    
                # Skip other API calls for now to simplify
                    
            return result
                    
        except Exception as e:
            logger.error(f"✗ Error getting UMLS concept details for {cui}: {e}")
            return result

    async def create_medical_collection(self, name: str, description: str = "") -> str:
        """
        Create a new collection for medical documents or return existing collection ID
        
        Args:
            name: Name of the collection
            description: Optional description for the collection
            
        Returns:
            str: Collection ID
        """
        # Check if we have a collection from a previous run
        if self.state.get("collection_id"):
            try:
                # Verify the existing collection still exists
                existing_collection = await self.retry_api_call(
                    self.client.collections.get,
                    id=self.state["collection_id"]
                )
                logger.info(f"Using existing collection ID: {self.state['collection_id']}")
                return self.state["collection_id"]
            except Exception:
                # If existing collection no longer exists, we'll create a new one
                logger.warning("Previous collection no longer exists, creating a new one")
                
        try:
            # First, try to list collections to see if one with this name already exists
            collections_response = await self.retry_api_call(
                self.client.collections.list
            )
                    
            # Check if a collection with the given name already exists
            for collection in collections_response.get('results', []):
                if collection.get('name') == name:
                    logger.info(f"Found existing collection {name} with ID {collection['id']}")
                    # Save the collection ID in our state
                    self.state["collection_id"] = collection['id']
                    self._save_state()
                    return collection['id']
                    
            # If no existing collection, create a new one
            response = await self.retry_api_call(
                self.client.collections.create,
                name=name,
                description=description or "Medical literature knowledge graph"
            )
            collection_id = response['results']['id']
            logger.info(f"✓ Created new collection {name} with ID {collection_id}")
                    
            # Save the collection ID in our state
            self.state["collection_id"] = collection_id
            self._save_state()
                    
            return collection_id
        except Exception as e:
            logger.error(f"✗ Failed to create or find collection: {e}")
            return None

    async def ingest_file(self, file_path: Path, pubid: str, collection_id: str) -> Optional[str]:
        """Ingest a single MD file into the specified collection"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Ingest with hi-res mode and associate with the given collection
            uuid_value = uuid.uuid4()
            response = await self.retry_api_call(
                self.client.documents.create,
                raw_text=content,
                id=str(uuid_value),
                collection_ids=[collection_id],
                metadata={
                    "title": file_path.stem,
                    "pubid": pubid,
                    "source": "pubmed",
                    "file_type": "markdown"
                },
                ingestion_mode="hi-res"
            )
            
            if isinstance(response, dict) and 'results' in response and 'document_id' in response['results']:
                doc_id = response['results']['document_id']
                logger.info(f"✓ Ingested {file_path.name} (PubID: {pubid}, ID: {doc_id})")
                
                # Add to our ingested documents set
                self.state.setdefault("ingested_docs", set()).add(doc_id)
                self._save_state()
                
                return doc_id
            else:
                logger.warning(f"✗ Unable to extract document ID for {file_path.name}")
                return None
        except Exception as e:
            logger.error(f"✗ Failed to ingest {file_path.name}: {e}")
            return None

    async def ingest_directory(self, directory: str, collection_id: str, max_papers: int = 10) -> List[str]:
        """Ingest MD files from the base directory"""
        directory_path = Path(directory)
        
        # Validate directory exists
        if not directory_path.exists():
            logger.error(f"Directory does not exist: {directory}")
            logger.error(f"Current working directory: {os.getcwd()}")
            raise ValueError(f"Directory {directory} does not exist")
        
        doc_ids = []
        # Find all subdirectories (PMC folders)
        pmc_dirs = [d for d in directory_path.iterdir() if d.is_dir()]
        logger.info(f"Found {len(pmc_dirs)} PMC directories")
        
        # Limit the number of papers if specified
        pmc_dirs = pmc_dirs[:max_papers]
        
        for pmc_dir in pmc_dirs:
            # Look for 'auto' subdirectory
            auto_dir = pmc_dir / 'auto'
            
            if auto_dir.exists():
                # Find markdown files in the 'auto' directory
                md_files = list(auto_dir.glob("*_with_tables.md"))
                logger.debug(f"Found {len(md_files)} markdown files in {auto_dir}")
                
                for md_file in md_files:
                    try:
                        # Use the parent directory (PMC folder) name as pubid
                        pubid = pmc_dir.name
                        
                        # Check if we already processed this file
                        file_key = f"{pubid}_{md_file.name}"
                        
                        # Ingest file and get document ID
                        doc_id = await self.ingest_file(md_file, pubid, collection_id)
                        if doc_id:
                            doc_ids.append(doc_id)
                            
                            # Save state periodically
                            if len(doc_ids) % 10 == 0:
                                self._save_state()
                    except Exception as e:
                        logger.error(f"Error ingesting {md_file}: {e}")
                        # Continue with the next file
        
        logger.info(f"Ingested {len(doc_ids)} documents from {directory}")
        self._save_state()  # Final save
        return doc_ids

    async def extract_entities_batch(self, doc_ids: List[str], batch_size=5, cooldown=30):
        """Extract medical entities from multiple documents in batches"""
        # Get only documents that haven't been processed yet
        pending_doc_ids = [doc_id for doc_id in doc_ids 
                          if doc_id not in self.state.get("entity_extracted_docs", set())]
        
        already_processed = len(doc_ids) - len(pending_doc_ids)
        if already_processed > 0:
            logger.info(f"Skipping {already_processed} documents that already have entity extraction")
            
        if not pending_doc_ids:
            logger.info("No documents need entity extraction")
            return list(self.state.get("entity_extracted_docs", set()))
            
        logger.info(f"Extracting entities from {len(pending_doc_ids)} documents in batches of {batch_size}")
        
        successful_extractions = []
        
        # Process documents in batches
        for i in range(0, len(pending_doc_ids), batch_size):
            batch = pending_doc_ids[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(pending_doc_ids) + batch_size - 1)//batch_size}")
            
            for doc_id in batch:
                try:
                    logger.info(f"Extracting entities from document {doc_id}")
                    
                    await self.retry_api_call(
                        self.client.documents.extract,
                        id=doc_id,
                        settings={
                            "prompt_template": self.MEDICAL_ENTITY_PROMPT,
                            "generation_config": {
                                "model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
                                "api_base": "http://10.10.65.64:8083/v1/",
                                "temperature": 0.3
                            },
                            "extraction_params": {
                                "min_confidence": 0.7,
                                "include_context": True
                            }
                        }
                    )
                    
                    logger.info(f"✓ Extracted entities from document {doc_id}")
                    successful_extractions.append(doc_id)
                    
                    # Update our state immediately
                    self.state.setdefault("entity_extracted_docs", set()).add(doc_id)
                    self._save_state()
                    
                    # Add a small delay between documents in the same batch
                    await asyncio.sleep(5 + random.uniform(0, 2))
                    
                except Exception as e:
                    logger.error(f"✗ Failed to extract entities from document {doc_id}: {e}")
            
            # Add a cooldown period between batches
            if i + batch_size < len(pending_doc_ids):
                cooldown_time = cooldown + random.uniform(0, 10)
                logger.info(f"Batch complete. Cooling down for {cooldown_time:.1f} seconds before next batch")
                await asyncio.sleep(cooldown_time)
        
        # Combine with previously extracted documents
        all_extracted = list(self.state.get("entity_extracted_docs", set()))
        logger.info(f"Entities successfully extracted from {len(successful_extractions)} new documents, {len(all_extracted)} total")
        
        return all_extracted

    async def extract_relationships_batch(self, doc_ids: List[str], batch_size=5, cooldown=30):
        """Extract medical relationships from multiple documents in batches"""
        # Get only documents that haven't been processed yet
        pending_doc_ids = [doc_id for doc_id in doc_ids 
                          if doc_id not in self.state.get("relationship_extracted_docs", set())]
        
        already_processed = len(doc_ids) - len(pending_doc_ids)
        if already_processed > 0:
            logger.info(f"Skipping {already_processed} documents that already have relationship extraction")
            
        if not pending_doc_ids:
            logger.info("No documents need relationship extraction")
            return list(self.state.get("relationship_extracted_docs", set()))
            
        logger.info(f"Extracting relationships from {len(pending_doc_ids)} documents in batches of {batch_size}")
        
        successful_extractions = []
        
        # Process documents in batches
        for i in range(0, len(pending_doc_ids), batch_size):
            batch = pending_doc_ids[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(pending_doc_ids) + batch_size - 1)//batch_size}")
            
            for doc_id in batch:
                try:
                    logger.info(f"Extracting relationships from document {doc_id}")
                    
                    await self.retry_api_call(
                        self.client.documents.extract,
                        id=doc_id,
                        settings={
                            "prompt_template": self.MEDICAL_RELATIONSHIP_PROMPT,
                            "generation_config": {
                                "model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
                                "api_base": "http://10.10.65.64:8083/v1/",
                                "temperature": 0.3
                            },
                            "extraction_params": {
                                "min_confidence": 0.7,
                            }
                        }
                    )
                    
                    logger.info(f"✓ Extracted relationships from document {doc_id}")
                    successful_extractions.append(doc_id)
                    
                    # Update our state immediately
                    self.state.setdefault("relationship_extracted_docs", set()).add(doc_id)
                    self._save_state()
                    
                    # Add a small delay between documents in the same batch
                    await asyncio.sleep(5 + random.uniform(0, 2))
                    
                except Exception as e:
                    logger.error(f"✗ Failed to extract relationships from document {doc_id}: {e}")
            
            # Add a cooldown period between batches
            if i + batch_size < len(pending_doc_ids):
                cooldown_time = cooldown + random.uniform(0, 10)
                logger.info(f"Batch complete. Cooling down for {cooldown_time:.1f} seconds before next batch")
                await asyncio.sleep(cooldown_time)
        
        # Combine with previously extracted documents
        all_extracted = list(self.state.get("relationship_extracted_docs", set()))
        logger.info(f"Relationships successfully extracted from {len(successful_extractions)} new documents, {len(all_extracted)} total")
        
        return all_extracted

    async def build_medical_kg(self, collection_id: str, doc_ids: List[str]):
        """Build knowledge graph for all documents within the specified collection."""
        try:
            logger.info(f"Starting knowledge graph build for collection: {collection_id}")
            
            # Update the graph with extracted information
            response = await self.retry_api_call(
                self.client.graphs.update,
                collection_id=collection_id,
                name="Medical Knowledge Graph",
                description="Extracted medical entities and relationships"
            )
            logger.info(f"✓ Updated graph metadata: {response}")
            
            # Pull entities and relationships into the graph
            logger.info("Pulling entities and relationships into graph...")
            await self.retry_api_call(
                self.client.graphs.pull,
                collection_id=collection_id
            )
            logger.info("✓ Pulled entities and relationships into graph")
            
            # Get entity and relationship counts
            entities = await self.client.graphs.list_entities(collection_id=collection_id)
            relationships = await self.client.graphs.list_relationships(collection_id=collection_id)
            
            logger.info(f"Knowledge graph built with {len(entities.get('results', []))} entities and {len(relationships.get('results', []))} relationships")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to build knowledge graph: {e}")
            return False

    async def create_umls_layer(self, collection_id: str):
        """Create a separate UMLS layer in the knowledge graph"""
        try:
            logger.info(f"Creating UMLS layer for collection: {collection_id}")
            
            # Create a "UMLS" parent entity to represent the UMLS layer
            umls_layer = await self.retry_api_call(
                self.client.graphs.create_entity,
                collection_id=collection_id,
                name="UMLS_Layer",
                description="UMLS concept hierarchy layer",
                category="Layer",
                metadata={
                    "layer_type": "ontology",
                    "version": "UMLS Latest"
                }
            )
            
            umls_layer_id = umls_layer['results']['id']
            logger.info(f"✓ Created UMLS layer entity with ID: {umls_layer_id}")
            
            # Get all entities in the graph
            entities_response = await self.retry_api_call(
                self.client.graphs.list_entities,
                collection_id=collection_id
            )
            
            entities = entities_response.get('results', [])
            if not entities:
                logger.warning("No entities found to map to UMLS layer")
                return False
                
            logger.info(f"Found {len(entities)} entities to process for UMLS mapping")
            
            # Track created UMLS concepts to avoid duplicates
            created_umls_concepts = {}
            
            # Process each entity and map to UMLS - use batches for large entity sets
            entity_count = len(entities)
            batch_size = 50  # Process 50 entities at a time
            
            for batch_start in range(0, entity_count, batch_size):
                batch_end = min(batch_start + batch_size, entity_count)
                logger.info(f"Processing UMLS mapping batch {batch_start//batch_size + 1}/{(entity_count + batch_size - 1)//batch_size} (entities {batch_start}-{batch_end-1})")
                
                for idx in range(batch_start, batch_end):
                    entity = entities[idx]
                    try:
                        # Skip UMLS layer and UMLS concepts
                        if entity.get('category') in ['Layer', 'UMLS_Concept']:
                            continue
                            
                        logger.info(f"Processing entity {idx+1}/{entity_count}: {entity['name']}")
                        
                        # Map to UMLS
                        umls_concept = await self.search_umls(entity['name'])
                        
                        if umls_concept and umls_concept.get('cui'):
                            cui = umls_concept['cui']
                            
                            # Check if this UMLS concept was already created
                            umls_entity_id = created_umls_concepts.get(cui)
                            
                            if not umls_entity_id:
                                # Format semantic types
                                semantic_types_str = ", ".join([
                                    st.get('type', '') for st in umls_concept.get('semantic_types', [])
                                ])
                                
                                # Get definition if available
                                definition = ""
                                if umls_concept.get('definitions'):
                                    definition = umls_concept['definitions'][0].get('value', '')
                                
                                # Create new UMLS concept entity
                                umls_entity = await self.retry_api_call(
                                    self.client.graphs.create_entity,
                                    collection_id=collection_id,
                                    name=umls_concept['preferred_term'],
                                    description=definition or f"UMLS Concept: {cui} - {semantic_types_str}",
                                    category="UMLS_Concept",
                                    metadata={
                                        "cui": cui,
                                        "semantic_types": semantic_types_str,
                                        "synonyms": umls_concept.get('synonyms', [])[:10],  # Limit to 10 synonyms
                                        "source": "UMLS"
                                    }
                                )
                                
                                umls_entity_id = umls_entity['results']['id']
                                created_umls_concepts[cui] = umls_entity_id
                                
                                # Connect UMLS concept to the UMLS layer
                                await self.retry_api_call(
                                    self.client.graphs.create_relationship,
                                    collection_id=collection_id,
                                    subject_id=umls_layer_id,
                                    description="Layer contains UMLS concept",
                                    subject="UMLS_Layer",
                                    predicate="contains",
                                    object_id=umls_entity_id,
                                    object=umls_concept['preferred_term']
                                )
                            
                            # Update original entity with UMLS metadata
                            await self.retry_api_call(
                                self.client.graphs.update,
                                collection_id=collection_id,
                                entity_id=entity['id'],
                                metadata={
                                    **entity.get('metadata', {}),
                                    "umls_cui": cui,
                                    "umls_preferred_term": umls_concept['preferred_term']
                                }
                            )
                            
                            # Create relationship between original entity and UMLS concept
                            await self.retry_api_call(
                                self.client.graphs.create_relationship,
                                collection_id=collection_id,
                                subject_id=entity['id'],
                                subject=entity['name'],
                                predicate="maps_to",
                                object_id=umls_entity_id,
                                object=umls_concept['preferred_term'],
                                description=f"Entity maps to UMLS concept {umls_concept['cui']}",
                                metadata={
                                    "confidence": "High",
                                    "mapping_type": "entity_to_umls"
                                }
                            )
                            
                            logger.info(f"✓ Mapped entity '{entity['name']}' to UMLS concept '{umls_concept['preferred_term']}' (CUI: {cui})")
                        else:
                            logger.debug(f"No UMLS mapping found for entity: {entity['name']}")
                        
                        # Small delay between entities to avoid rate limiting
                        await asyncio.sleep(0.2)
                            
                    except Exception as e:
                        logger.error(f"✗ Error mapping entity '{entity['name']}' to UMLS: {e}")
                
                # Add a cooldown period between batches
                if batch_end < entity_count:
                    logger.info(f"Waiting 30 seconds between UMLS mapping batches...")
                    await asyncio.sleep(30)
            
            logger.info(f"✓ Created UMLS layer with {len(created_umls_concepts)} UMLS concepts")
            
            # Add hierarchical relationships between UMLS concepts
            await self._add_umls_hierarchical_relationships(collection_id, created_umls_concepts)
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to create UMLS layer: {e}")
            return False

    async def _add_umls_hierarchical_relationships(self, collection_id: str, umls_concepts: Dict[str, str]):
        """Add hierarchical relationships between UMLS concepts"""
        try:
            logger.info(f"Adding hierarchical relationships between UMLS concepts")
            
            relationships_created = 0
            
            # For each UMLS concept, create relationships with its parents and children
            cui_list = list(umls_concepts.keys())
            batch_size = 50  # Process 50 concepts at a time
            
            for batch_start in range(0, len(cui_list), batch_size):
                batch_end = min(batch_start + batch_size, len(cui_list))
                logger.info(f"Processing UMLS hierarchical relationships batch {batch_start//batch_size + 1}/{(len(cui_list) + batch_size - 1)//batch_size}")
                
                for idx in range(batch_start, batch_end):
                    cui = cui_list[idx]
                    entity_id = umls_concepts[cui]
                    
                    # Get concept details with parent/child information
                    concept_details = await self._get_umls_concept_details(cui)
                    
                    # Process parent relationships
                    for parent in concept_details.get('parents', []):
                        parent_cui = parent.get('cui')
                        if parent_cui in umls_concepts:
                            try:
                                await self.retry_api_call(
                                    self.client.graphs.create_relationship,
                                    collection_id=collection_id,
                                    subject_id=entity_id,  # Current concept
                                    subject=concept_details.get('preferred_term', f"UMLS:{cui}"),
                                    predicate="is_a",  # Hierarchical relationship
                                    object_id=umls_concepts[parent_cui],  # Parent concept
                                    object=f"UMLS:{parent_cui}",
                                    description=f"Hierarchical relationship from UMLS ({parent.get('relation_type', 'parent')})",
                                    metadata={
                                        "relation_source": "umls",
                                        "relation_type": parent.get('relation_type')
                                    }
                                )
                                relationships_created += 1
                            except Exception as e:
                                logger.error(f"✗ Error creating UMLS parent relationship: {e}")
                    
                    # Wait to avoid rate limiting
                    await asyncio.sleep(0.2)
                
                # Add a cooldown period between batches
                if batch_end < len(cui_list):
                    logger.info(f"Waiting 30 seconds between UMLS hierarchical relationship batches...")
                    await asyncio.sleep(30)
            
            logger.info(f"✓ Created {relationships_created} hierarchical relationships between UMLS concepts")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to create UMLS hierarchical relationships: {e}")
            return False

    async def create_medical_terminology_layer(self, collection_id: str):
        """Create a medical terminology layer that works with or without UMLS"""
        try:
            logger.info(f"Creating medical terminology layer for collection: {collection_id}")
            
            # Create the layer entity
            layer_entity = await self.retry_api_call(
                self.client.graphs.create_entity,
                collection_id=collection_id,
                name="Medical_Terminology_Layer",
                description="Standardized medical terminology layer",
                category="Layer",
                metadata={
                    "layer_type": "terminology",
                    "source": "mixed"  # Can come from UMLS or local normalization
                }
            )
            
            layer_id = layer_entity['results']['id']
            logger.info(f"✓ Created terminology layer with ID: {layer_id}")
            
            # Get all entities in the graph
            entities_response = await self.retry_api_call(
                self.client.graphs.list_entities,
                collection_id=collection_id
            )
            
            if not entities_response or 'results' not in entities_response:
                logger.warning("Failed to retrieve entities from the graph")
                return False
                
            entities = entities_response.get('results', [])
            if not entities:
                logger.warning("No entities found to map to terminology layer")
                return False
                
            logger.info(f"Found {len(entities)} entities to process for terminology mapping")
            
            # Track created concept entities to avoid duplicates
            concept_map = {}  # Maps normalized term -> entity ID
            umls_mapped = 0
            locally_mapped = 0
            
            # Process entities in batches
            entity_count = len(entities)
            batch_size = 50  # Process 50 entities at a time
            
            for batch_start in range(0, entity_count, batch_size):
                batch_end = min(batch_start + batch_size, entity_count)
                logger.info(f"Processing terminology mapping batch {batch_start//batch_size + 1}/{(entity_count + batch_size - 1)//batch_size} (entities {batch_start}-{batch_end-1})")
                
                for idx in range(batch_start, batch_end):
                    entity = entities[idx]
                    try:
                        # Skip layer entities and already processed concepts
                        if not entity or 'id' not in entity or 'name' not in entity:
                            continue
                            
                        if entity.get('category') in ['Layer', 'Medical_Concept', 'UMLS_Concept']:
                            continue
                        
                        entity_name = entity['name']
                        entity_id = entity['id']
                        entity_type = entity.get('category', 'Unknown')
                        
                        logger.info(f"Processing entity {idx+1}/{entity_count}: {entity_name}")
                        
                        # Try UMLS mapping first if API key is available
                        umls_mapped_successfully = False
                        umls_concept = None
                        
                        if self.umls_api_key:
                            try:
                                umls_concept = await self.search_umls(entity_name)
                                if umls_concept and isinstance(umls_concept, dict) and 'cui' in umls_concept:
                                    umls_mapped_successfully = True
                            except Exception as e:
                                logger.warning(f"UMLS mapping failed for '{entity_name}': {e}")
                        
                        # If UMLS mapping worked, use that
                        if umls_mapped_successfully:
                            cui = umls_concept['cui']
                            preferred_name = umls_concept.get('preferred_term') or entity_name
                            
                            # Check if we already created this concept
                            concept_id = concept_map.get(cui)
                            
                            if not concept_id:
                                # Create the concept entity
                                concept = await self.retry_api_call(
                                    self.client.graphs.create_entity,
                                    collection_id=collection_id,
                                    name=preferred_name, 
                                    description=f"UMLS Concept: {cui}",
                                    category="Medical_Concept",
                                    metadata={
                                        "cui": cui,
                                        "source": "UMLS"
                                    }
                                )
                                
                                concept_id = concept['results']['id']
                                concept_map[cui] = concept_id
                                
                                # Connect to the layer
                                await self.retry_api_call(
                                    self.client.graphs.create_relationship,
                                    collection_id=collection_id,
                                    subject_id=layer_id,
                                    subject="Medical_Terminology_Layer",
                                    predicate="contains",
                                    object_id=concept_id,
                                    object=preferred_name,
                                    description="Layer contains standardized medical concept"
                                )
                            
                            # Map the original entity to this concept
                            await self.retry_api_call(
                                self.client.graphs.create_relationship,
                                collection_id=collection_id,
                                subject_id=entity_id,
                                subject=entity_name,
                                predicate="maps_to",
                                object_id=concept_id,
                                object=preferred_name,
                                description=f"Entity maps to UMLS concept {cui}"
                            )
                            
                            umls_mapped += 1
                            logger.info(f"✓ Mapped '{entity_name}' to UMLS concept '{preferred_name}' (CUI: {cui})")
                            
                        # Otherwise, fall back to local normalization
                        else:
                            # Create a normalized key
                            normalized_name = entity_name.lower().strip()
                            normalized_key = f"{normalized_name}_{entity_type}"
                            
                            # Check if we already have a concept for this
                            concept_id = concept_map.get(normalized_key)
                            
                            if not concept_id:
                                # Create the concept entity
                                concept = await self.retry_api_call(
                                    self.client.graphs.create_entity,
                                    collection_id=collection_id,
                                    name=entity_name,
                                    description=f"Standardized medical term: {entity_name}",
                                    category="Medical_Concept",
                                    metadata={
                                        "normalized_name": normalized_name,
                                        "entity_type": entity_type,
                                        "source": "local_normalization"
                                    }
                                )
                                
                                concept_id = concept['results']['id']
                                concept_map[normalized_key] = concept_id
                                
                                # Connect to the layer
                                await self.retry_api_call(
                                    self.client.graphs.create_relationship,
                                    collection_id=collection_id,
                                    subject_id=layer_id,
                                    subject="Medical_Terminology_Layer",
                                    predicate="contains",
                                    object_id=concept_id,
                                    object=entity_name,
                                    description="Layer contains locally normalized concept"
                                )
                            
                            # Map the original entity to this concept
                            await self.retry_api_call(
                                self.client.graphs.create_relationship,
                                collection_id=collection_id,
                                subject_id=entity_id,
                                subject=entity_name,
                                predicate="normalized_as",
                                object_id=concept_id,
                                object=entity_name,
                                description=f"Entity normalized to standard term"
                            )
                            
                            locally_mapped += 1
                            logger.info(f"✓ Locally normalized '{entity_name}'")
                        
                        # Wait to avoid overloading the server
                        await asyncio.sleep(0.1)
                            
                    except Exception as e:
                        logger.error(f"✗ Error processing entity '{entity.get('name', 'unknown')}': {e}")
                
                # Add a cooldown period between batches
                if batch_end < entity_count:
                    logger.info(f"Waiting 30 seconds between terminology mapping batches...")
                    await asyncio.sleep(30)
            
            # Log summary statistics
            total_concepts = len(concept_map)
            logger.info(f"✓ Created terminology layer with {total_concepts} standardized concepts")
            logger.info(f"  - UMLS mapped: {umls_mapped}")
            logger.info(f"  - Locally normalized: {locally_mapped}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to create terminology layer: {e}")
            return False
    async def ingest_mri_with_markdown(self, image_path: Path, collection_id: str) -> Optional[str]:
        """
        Ingest an MRI image with its associated markdown description
        
        Args:
            image_path: Path to the MRI image
            collection_id: The collection to add the image to
            
        Returns:
            str: Document ID of the ingested image or None if failed
        """
        try:
            # Check if image file exists
            if not image_path.exists():
                logger.error(f"Image file does not exist: {image_path}")
                return None
                
            # Find corresponding markdown file (same name but .md extension)
            md_path = image_path.with_suffix('.md')
            if not md_path.exists():
                logger.warning(f"No markdown description found for {image_path.name}, using default metadata")
                metadata = {
                    "title": f"MRI Image: {image_path.name}",
                    "use_case": "Unknown",
                    "clinical_context": "Not specified",
                    "findings": "Not specified"
                }
            else:
                # Parse the markdown file to extract metadata
                metadata = self._parse_markdown_description(md_path)
                logger.info(f"Parsed metadata from {md_path}")
            
            # Add image-specific metadata
            metadata["content_type"] = "mri_image"
            metadata["file_type"] = image_path.suffix.lstrip('.')
            metadata["source"] = "mri_database"
            
            # Create a unique ID based on image name
            image_uuid = uuid.uuid4()
            
            # Ingest the image with hi-res mode
            response = await self.retry_api_call(
                self.client.documents.create,
                file_path=str(image_path),
                id=str(image_uuid),
                collection_ids=[collection_id],
                metadata=metadata,
                ingestion_mode="hi-res"
            )
            
            if isinstance(response, dict) and 'results' in response and 'document_id' in response['results']:
                doc_id = response['results']['document_id']
                logger.info(f"✓ Ingested MRI image {image_path.name} (ID: {doc_id})")
                
                # Also ingest the markdown file as a separate document with relationship to the image
                if md_path.exists():
                    md_uuid = uuid.uuid4()
                    md_response = await self.retry_api_call(
                        self.client.documents.create,
                        file_path=str(md_path),
                        id=str(md_uuid),
                        collection_ids=[collection_id],
                        metadata={
                            "title": f"Description for {image_path.name}",
                            "content_type": "mri_description",
                            "related_image_id": doc_id,
                            "source": "mri_database"
                        },
                        ingestion_mode="hi-res"
                    )
                    
                    if isinstance(md_response, dict) and 'results' in md_response and 'document_id' in md_response['results']:
                        md_doc_id = md_response['results']['document_id']
                        logger.info(f"✓ Ingested MRI description {md_path.name} (ID: {md_doc_id})")
                        
                        # Add to our ingested documents set
                        self.state.setdefault("ingested_docs", set()).add(md_doc_id)
                
                # Add image to our ingested documents set
                self.state.setdefault("ingested_docs", set()).add(doc_id)
                self._save_state()
                
                return doc_id
            else:
                logger.warning(f"✗ Unable to extract document ID for MRI image {image_path.name}")
                return None
                
        except Exception as e:
            logger.error(f"✗ Failed to ingest MRI image {image_path.name}: {e}")
            return None
    def _parse_markdown_description(self, md_path: Path) -> Dict[str, Any]:
        """
        Parse a markdown file to extract metadata about an MRI image
        
        Expected MD format:
        # Title of the MRI Case
        
        ## Clinical Context
        Patient information and context
        
        ## Use Case
        The purpose of this MRI
        
        ## Findings
        Observations and diagnosis
        
        ## Additional Notes
        Any other relevant information
        
        Returns:
            Dict containing extracted metadata
        """
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            metadata = {
                "title": "MRI Case",
                "clinical_context": "",
                "use_case": "",
                "findings": "",
                "additional_notes": ""
            }
            
            # Extract title (assumes first line is a # heading)
            title_match = re.search(r'#\s+(.+)$', content, re.MULTILINE)
            if title_match:
                metadata["title"] = title_match.group(1).strip()
            
            # Extract sections
            sections = {
                "clinical_context": r'##\s+Clinical\s+Context\s*\n(.*?)(?=##|\Z)',
                "use_case": r'##\s+Use\s+Case\s*\n(.*?)(?=##|\Z)',
                "findings": r'##\s+Findings\s*\n(.*?)(?=##|\Z)',
                "additional_notes": r'##\s+Additional\s+Notes\s*\n(.*?)(?=##|\Z)'
            }
            
            for key, pattern in sections.items():
                match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
                if match:
                    metadata[key] = match.group(1).strip()
            
            # Add full content as well
            metadata["full_description"] = content
            
            return metadata
        except Exception as e:
            logger.error(f"Error parsing markdown file {md_path}: {e}")
            return {
                "title": f"MRI Image: {md_path.stem}",
                "error": f"Failed to parse markdown: {str(e)}"
            }
    async def ingest_mri_directory(self, directory: str, collection_id: str, max_images: int = 50) -> List[str]:
        """
        Ingest MRI images and their markdown descriptions from a directory
        
        Args:
            directory: Path to directory containing MRI images (.jpg, .png) and descriptions (.md)
            collection_id: Collection ID to add images to
            max_images: Maximum number of images to process
            
        Returns:
            List[str]: List of document IDs for ingested images
        """
        directory_path = Path(directory)
        
        # Validate directory exists
        if not directory_path.exists():
            logger.error(f"Directory does not exist: {directory}")
            raise ValueError(f"Directory {directory} does not exist")
        
        # Find image files in the directory
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            image_files.extend(list(directory_path.glob(ext)))
        
        logger.info(f"Found {len(image_files)} image files in {directory}")
        
        # Limit the number of images if specified
        image_files = image_files[:max_images]
        
        # Process each image
        doc_ids = []
        for image_file in image_files:
            # Check if corresponding .md file exists
            md_file = image_file.with_suffix('.md')
            if not md_file.exists():
                logger.warning(f"No markdown description found for {image_file.name}")
            
            # Ingest the image with its markdown description
            doc_id = await self.ingest_mri_with_markdown(image_file, collection_id)
            if doc_id:
                doc_ids.append(doc_id)
                
                # Save state periodically
                if len(doc_ids) % 10 == 0:
                    self._save_state()
        
        logger.info(f"Ingested {len(doc_ids)} MRI images from {directory}")
        self._save_state()  # Final save
        return doc_ids

async def main():
    # Initialize pipeline with robust error handling
    pipeline = MedicalKGPipeline(
        base_url="http://jovana.openbrain.io:7272",
        max_retries=3,
        retry_delay=10
    )
    
    # Create medical collection
    # collection_id = await pipeline.create_medical_collection(
    #     name="PubMed Papers Analysis",
    #     description="Knowledge graph from medical literature"
    # )
    collection_id = "215fee4b-40be-4429-ab26-60ac11c11a63"
    
    # Verify collection ID was created
    if not collection_id:
        logger.error("Failed to create collection")
        return
    
    # Set the output directory path
    output_dir = os.path.expanduser("/home/jovana/google-drive-new/Phd research/output")
    
    # # Step 1: Ingest all MD files
    # doc_ids = await pipeline.ingest_directory(
    #     output_dir,
    #     collection_id,
    #     max_papers=1000 # Process up to 1000 papers
    # )
    try:
        # List all documents in the collection
        documents_response = await pipeline.retry_api_call(
            pipeline.client.collections.list_documents,  # Use collections endpoint instead
            id=collection_id,
            limit=1000  # Adjust as needed
        )
        
        doc_ids = [doc.get('id') for doc in documents_response.get('results', []) if 'id' in doc]
        logger.info(f"Found {len(doc_ids)} already ingested documents")
        
        # Update the state with these document IDs
        pipeline.state.setdefault("ingested_docs", set()).update(doc_ids)
        pipeline._save_state()
            
    except Exception as e:
        logger.error(f"Failed to retrieve ingested documents: {e}")
        return
        
    # Exit if no documents were processed
    if not doc_ids:
        logger.warning("No documents were ingested.")
        return
    
    logger.info(f"Total documents ingested: {len(doc_ids)}")
    
    # Step 2: Extract Entities with batch processing
    entity_extracted_doc_ids = await pipeline.extract_entities_batch(
        doc_ids, 
        batch_size=5,  # Process 5 docs at a time
        cooldown=60    # 1 minute between batches
    )
    logger.info(f"Entities extracted from {len(entity_extracted_doc_ids)} documents")
    
    # Step 3: Extract Relationships with batch processing
    relationship_extracted_doc_ids = await pipeline.extract_relationships_batch(
        doc_ids,
        batch_size=5,  # Process 5 docs at a time
        cooldown=60    # 1 minute between batches
    )
    logger.info(f"Relationships extracted from {len(relationship_extracted_doc_ids)} documents")
    
    # Step 4: Build Knowledge Graph
    build_medical_kg_status = await pipeline.build_medical_kg(
        collection_id=collection_id, 
        doc_ids=doc_ids
    )
    logger.info(f"Knowledge graph build status: {build_medical_kg_status}")
    
    # Step 5: Create terminology layer
    if build_medical_kg_status:
        logger.info("Creating medical terminology layer in the knowledge graph...")
        terminology_layer_status = await pipeline.create_medical_terminology_layer(collection_id)
        logger.info(f"Medical terminology layer creation status: {terminology_layer_status}")

async def mainMRI():
    # Initialize pipeline with robust error handling
    pipeline = MedicalKGPipeline(
        base_url="http://jovana.openbrain.io:7272",
        max_retries=3,
        retry_delay=10
    )
    
    # Create a dedicated MRI collection
    mri_collection_id = await pipeline.create_mri_collection(
        name="MRI Case Studies",
        description="Collection of MRI images with clinical descriptions and findings"
    )
    
    # Set the MRI directory path
    mri_dir = os.path.expanduser("/home/jovana/MRI_usecases")  # Directory with both JPGs and MDs
    
    # Ingest MRI images with their descriptions into the dedicated collection
    mri_doc_ids = await pipeline.ingest_mri_directory(
        mri_dir,
        mri_collection_id,
        max_images=100
    )
    
    if not mri_doc_ids:
        logger.warning("No MRI documents were ingested.")
        return
    
    logger.info(f"Total MRI documents ingested: {len(mri_doc_ids)}")
    
    # Extract entities with specialized MRI prompt
    entity_extracted_doc_ids = await pipeline.extract_entities_batch(
        mri_doc_ids, 
        batch_size=5,
        cooldown=60
    )
    logger.info(f"Entities extracted from {len(entity_extracted_doc_ids)} MRI documents")
    
    # Extract relationships with specialized MRI relationship prompt
    relationship_extracted_doc_ids = await pipeline.extract_relationships_batch(
        mri_doc_ids,
        batch_size=5,
        cooldown=60
    )
    logger.info(f"Relationships extracted from {len(relationship_extracted_doc_ids)} MRI documents")
    
    # Build MRI-specific Knowledge Graph
    build_mri_kg_status = await pipeline.build_medical_kg(
        collection_id=mri_collection_id, 
        doc_ids=mri_doc_ids
    )
    logger.info(f"MRI knowledge graph build status: {build_mri_kg_status}")
    
    # Create terminology layer specific to radiological findings
    if build_mri_kg_status:
        logger.info("Creating medical terminology layer in the MRI knowledge graph...")
        terminology_layer_status = await pipeline.create_medical_terminology_layer(mri_collection_id)
        logger.info(f"Medical terminology layer creation status: {terminology_layer_status}")
        
        # Optional: Create additional radiology-specific layer
        await pipeline.create_radiology_layer(mri_collection_id)

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the pipeline
    asyncio.run(mainMRI())