"""Configuration settings for S3 testing with folder-based access"""

# S3 configuration
S3_BUCKET = '1000-resilabs-caleb-dev-bittensor-sn46-datacollection'  # Development bucket
S3_REGION = 'us-east-2'              # US East (Ohio)

# Test data parameters (update with your actual keys for testing)
MINER_COLDKEY = '5FbQvuKPvfr3ckw27bNRp9unTtA5vVHUyeTecQJ3eLZF4xMK'  # Coldkey for authentication
MINER_HOTKEY = '5FTyhanxkXXGYhKL7L5UGTYmUBTk3vPFLJKNZZ9tN2eZ9Zcp'   # Hotkey for operations
SOURCE = '4'  # Subnet 46 data source

# Server configuration
SERVER_PORT = 8000
SERVER_HOST = '0.0.0.0'

# Rate limiting configuration
DAILY_LIMIT_PER_MINER = 20
HOURLY_LIMIT_PER_VALIDATOR = 30
TOTAL_DAILY_LIMIT = 2000

# Path structure
# data/SOURCE/COLDKEY/HOTKEY/filename.parquet