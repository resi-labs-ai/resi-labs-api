#!/usr/bin/env python3
"""
Import zipcode data from JSON/CSV into the database
"""
import os
import sys
import json
import csv
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from s3_storage_api.database import AsyncSessionLocal, init_database
from s3_storage_api.models.zipcode import Zipcode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ZipcodeDataImporter:
    """Import zipcode data from various sources"""
    
    def __init__(self):
        self.imported_count = 0
        self.updated_count = 0
        self.error_count = 0
    
    async def import_from_json(self, json_file_path: str) -> None:
        """Import zipcode data from JSON file"""
        logger.info(f"Importing zipcode data from {json_file_path}")
        
        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            zipcodes_data = data.get('zipcodes', [])
            logger.info(f"Found {len(zipcodes_data)} zipcodes in JSON file")
            
            async with AsyncSessionLocal() as db:
                for zipcode_data in zipcodes_data:
                    await self._import_single_zipcode(db, zipcode_data)
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error importing from JSON: {str(e)}")
            raise
    
    async def import_from_csv(self, csv_file_path: str) -> None:
        """Import zipcode data from CSV file"""
        logger.info(f"Importing zipcode data from {csv_file_path}")
        
        try:
            zipcodes_data = []
            with open(csv_file_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert CSV row to our expected format
                    zipcode_data = {
                        'zipcode': row['zipcode'],
                        'state': row['state'],
                        'city': row['city'],
                        'county': row.get('county'),
                        'population': int(row['population']) if row.get('population') else None,
                        'median_home_value': int(row['median_home_value']) if row.get('median_home_value') else None,
                        'recently_sold_listings': int(row['recently_sold_listings']),
                        'market_tier': row['market_tier'],
                        'geographic_region': row.get('geographic_region'),
                        'last_scraped': row.get('last_scraped')
                    }
                    zipcodes_data.append(zipcode_data)
            
            logger.info(f"Found {len(zipcodes_data)} zipcodes in CSV file")
            
            async with AsyncSessionLocal() as db:
                for zipcode_data in zipcodes_data:
                    await self._import_single_zipcode(db, zipcode_data)
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error importing from CSV: {str(e)}")
            raise
    
    async def _import_single_zipcode(self, db: AsyncSession, zipcode_data: Dict) -> None:
        """Import or update a single zipcode record"""
        try:
            zipcode = zipcode_data['zipcode']
            
            # Check if zipcode already exists
            existing = await db.get(Zipcode, zipcode)
            
            if existing:
                # Update existing record
                existing.state = zipcode_data['state']
                existing.city = zipcode_data['city']
                existing.county = zipcode_data.get('county')
                existing.population = zipcode_data.get('population')
                existing.median_home_value = zipcode_data.get('median_home_value')
                existing.expected_listings = zipcode_data.get('recently_sold_listings', zipcode_data.get('expected_listings', 0))
                existing.market_tier = zipcode_data['market_tier']
                existing.geographic_region = zipcode_data.get('geographic_region')
                existing.data_updated_at = datetime.utcnow()
                existing.data_source = 'import_script'
                existing.updated_at = datetime.utcnow()
                
                self.updated_count += 1
                logger.debug(f"Updated zipcode {zipcode}")
                
            else:
                # Create new record
                new_zipcode = Zipcode(
                    zipcode=zipcode,
                    state=zipcode_data['state'],
                    city=zipcode_data['city'],
                    county=zipcode_data.get('county'),
                    population=zipcode_data.get('population'),
                    median_home_value=zipcode_data.get('median_home_value'),
                    expected_listings=zipcode_data.get('recently_sold_listings', zipcode_data.get('expected_listings', 0)),
                    market_tier=zipcode_data['market_tier'],
                    geographic_region=zipcode_data.get('geographic_region'),
                    data_updated_at=datetime.utcnow(),
                    data_source='import_script',
                    is_active=True,
                    is_honeypot=False,
                    base_selection_weight=1.0
                )
                
                db.add(new_zipcode)
                self.imported_count += 1
                logger.debug(f"Imported new zipcode {zipcode}")
                
        except Exception as e:
            logger.error(f"Error importing zipcode {zipcode_data.get('zipcode', 'unknown')}: {str(e)}")
            self.error_count += 1
    
    async def generate_sample_data(self, count: int = 50) -> None:
        """Generate sample zipcode data for testing"""
        logger.info(f"Generating {count} sample zipcode records")
        
        # Sample data for PA/NJ area
        sample_zipcodes = [
            # Pennsylvania
            {"zipcode": "19102", "state": "PA", "city": "Philadelphia", "county": "Philadelphia County", "population": 45230, "median_home_value": 425000, "expected_listings": 1250, "market_tier": "premium"},
            {"zipcode": "19103", "state": "PA", "city": "Philadelphia", "county": "Philadelphia County", "population": 38920, "median_home_value": 520000, "expected_listings": 890, "market_tier": "premium"},
            {"zipcode": "19107", "state": "PA", "city": "Philadelphia", "county": "Philadelphia County", "population": 42150, "median_home_value": 445000, "expected_listings": 1100, "market_tier": "premium"},
            {"zipcode": "19460", "state": "PA", "city": "Phoenixville", "county": "Chester County", "population": 16788, "median_home_value": 385000, "expected_listings": 245, "market_tier": "standard"},
            {"zipcode": "19464", "state": "PA", "city": "Pottstown", "county": "Montgomery County", "population": 22377, "median_home_value": 195000, "expected_listings": 420, "market_tier": "emerging"},
            {"zipcode": "19380", "state": "PA", "city": "West Chester", "county": "Chester County", "population": 18461, "median_home_value": 410000, "expected_listings": 380, "market_tier": "premium"},
            {"zipcode": "19406", "state": "PA", "city": "King of Prussia", "county": "Montgomery County", "population": 19936, "median_home_value": 385000, "expected_listings": 520, "market_tier": "standard"},
            {"zipcode": "19335", "state": "PA", "city": "Downingtown", "county": "Chester County", "population": 7891, "median_home_value": 365000, "expected_listings": 220, "market_tier": "standard"},
            
            # New Jersey
            {"zipcode": "08540", "state": "NJ", "city": "Princeton", "county": "Mercer County", "population": 28450, "median_home_value": 780000, "expected_listings": 320, "market_tier": "premium"},
            {"zipcode": "07030", "state": "NJ", "city": "Hoboken", "county": "Hudson County", "population": 55131, "median_home_value": 650000, "expected_listings": 1450, "market_tier": "premium"},
            {"zipcode": "08701", "state": "NJ", "city": "Lakewood", "county": "Ocean County", "population": 102682, "median_home_value": 285000, "expected_listings": 1850, "market_tier": "standard"},
            {"zipcode": "08360", "state": "NJ", "city": "Vineland", "county": "Cumberland County", "population": 60724, "median_home_value": 165000, "expected_listings": 680, "market_tier": "emerging"},
            {"zipcode": "08002", "state": "NJ", "city": "Cherry Hill", "county": "Camden County", "population": 71045, "median_home_value": 320000, "expected_listings": 950, "market_tier": "standard"},
            {"zipcode": "08003", "state": "NJ", "city": "Cherry Hill", "county": "Camden County", "population": 65432, "median_home_value": 295000, "expected_listings": 780, "market_tier": "standard"},
            {"zipcode": "08901", "state": "NJ", "city": "New Brunswick", "county": "Middlesex County", "population": 55181, "median_home_value": 285000, "expected_listings": 890, "market_tier": "standard"},
        ]
        
        # Generate additional sample data
        import random
        base_zipcodes = sample_zipcodes.copy()
        
        while len(sample_zipcodes) < count:
            # Create variations of existing zipcodes
            base = random.choice(base_zipcodes)
            new_zipcode = base.copy()
            
            # Generate new zipcode number
            if base['state'] == 'PA':
                new_zipcode['zipcode'] = f"19{random.randint(100, 999)}"
            else:  # NJ
                new_zipcode['zipcode'] = f"08{random.randint(100, 999)}"
            
            # Vary the data slightly
            new_zipcode['population'] = random.randint(10000, 100000)
            new_zipcode['median_home_value'] = random.randint(150000, 800000)
            new_zipcode['expected_listings'] = random.randint(100, 2000)
            
            # Assign market tier based on home value
            if new_zipcode['median_home_value'] >= 400000:
                new_zipcode['market_tier'] = 'premium'
            elif new_zipcode['median_home_value'] >= 200000:
                new_zipcode['market_tier'] = 'standard'
            else:
                new_zipcode['market_tier'] = 'emerging'
            
            sample_zipcodes.append(new_zipcode)
        
        # Import the sample data
        async with AsyncSessionLocal() as db:
            for zipcode_data in sample_zipcodes[:count]:
                zipcode_data['geographic_region'] = 'Mid-Atlantic'
                await self._import_single_zipcode(db, zipcode_data)
            
            await db.commit()
    
    def print_summary(self):
        """Print import summary"""
        logger.info("=" * 50)
        logger.info("ZIPCODE DATA IMPORT SUMMARY")
        logger.info("=" * 50)
        logger.info(f"New records imported: {self.imported_count}")
        logger.info(f"Existing records updated: {self.updated_count}")
        logger.info(f"Errors encountered: {self.error_count}")
        logger.info(f"Total processed: {self.imported_count + self.updated_count + self.error_count}")

async def main():
    """Main import function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import zipcode data into database')
    parser.add_argument('--json', help='Path to JSON file to import')
    parser.add_argument('--csv', help='Path to CSV file to import') 
    parser.add_argument('--sample', type=int, help='Generate N sample records for testing')
    parser.add_argument('--init-db', action='store_true', help='Initialize database first')
    
    args = parser.parse_args()
    
    if not any([args.json, args.csv, args.sample]):
        parser.error('Must specify --json, --csv, or --sample')
    
    # Initialize database if requested
    if args.init_db:
        logger.info("Initializing database...")
        await init_database()
    
    importer = ZipcodeDataImporter()
    
    try:
        if args.json:
            await importer.import_from_json(args.json)
        elif args.csv:
            await importer.import_from_csv(args.csv)
        elif args.sample:
            await importer.generate_sample_data(args.sample)
        
        importer.print_summary()
        
    except Exception as e:
        logger.error(f"Import failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
