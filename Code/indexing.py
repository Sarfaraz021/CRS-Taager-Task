import os
import glob
import asyncio
import time
from typing import List
from dotenv import load_dotenv
from tqdm import tqdm
from pinecone import Pinecone, PodSpec

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_community.document_loaders import TextLoader

DATA_DIR = r"D:\CRS-Taager-Task\Data"


class DocumentIndexer:
    def __init__(self):
        self.setup_environment()
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.pinecone_client = self._init_pinecone()
        self.vectorstore = self._get_or_create_index()
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )

    def setup_environment(self):
        """Set up environment variables from .env file"""
        load_dotenv('var.env')
        required_vars = ['OPENAI_API_KEY', 'PINECONE_API_KEY', 'PINECONE_INDEX_NAME']
        for var in required_vars:
            if not os.getenv(var):
                raise ValueError(f"{var} not found in environment variables")

    def _init_pinecone(self) -> Pinecone:
        """Initialize Pinecone client"""
        return Pinecone(
            api_key=os.getenv('PINECONE_API_KEY'),
            environment="us-east-1-aws"
        )

    def _get_or_create_index(self) -> PineconeVectorStore:
        """Get existing Pinecone index or create a new one"""
        index_name = os.getenv('PINECONE_INDEX_NAME')
        
        index = self.pinecone_client.Index(index_name)
        return PineconeVectorStore(index=index, embedding=self.embeddings)

    def metadata_func(self, record: dict, metadata: dict) -> dict:
        """Extract metadata from JSON record"""
        # Add any available fields from the record to metadata
        for key, value in record.items():
            if isinstance(value, (str, int, float, bool)):
                metadata[key] = value
        return metadata

    async def process_file(self, file_path: str) -> bool:
        """Process a single file (PDF or JSON) and add it to the vector store"""
        try:
            print(f"\nProcessing: {os.path.basename(file_path)}")
            
            
            loader = TextLoader(file_path)
            documents = loader.load()
            
            # Add common metadata to documents
            for doc in documents:
                doc.metadata["source_file"] = os.path.basename(file_path)
                doc.metadata["full_path"] = file_path
                doc.metadata["date_indexed"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Split documents and add to vector store
            docs = self.text_splitter.split_documents(documents)
            self.vectorstore.add_documents(docs)
            return True
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            return False

    async def batch_process_files(self):
        """Process all files in the data directory"""
        # Get all files
        txt_files = glob.glob(os.path.join(DATA_DIR, "**/*.txt"), recursive=True)
        all_files = txt_files
        
        if not all_files:
            print(f"No PDF or JSON files found in {DATA_DIR}")
            return
        
        print(f"\nFound {len(all_files)} files to process ({len(pdf_files)} PDFs, {len(json_files)} JSONs)")
        
        successful = 0
        failed = 0
        
        with tqdm(total=len(all_files), desc="Processing files") as pbar:
            for file_path in all_files:
                try:
                    success = await self.process_file(file_path)
                    if success:
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    print(f"\nUnexpected error processing {file_path}: {str(e)}")
                    failed += 1
                pbar.update(1)

        print("\nProcessing complete!")
        print(f"Successfully processed: {successful} files")
        print(f"Failed to process: {failed} files")

async def main():
    indexer = DocumentIndexer()
    await indexer.batch_process_files()

if __name__ == "__main__":
    asyncio.run(main())