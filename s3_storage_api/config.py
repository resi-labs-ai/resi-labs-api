"""Configuration settings for S3 testing with folder-based access"""

# S3 configuration
S3_BUCKET = 'data-universe-storage'  # Change to your bucket name
S3_REGION = 'us-east-1'              # Change to your region

# Test data parameters
MINER_COLDKEY = '5FbQvuKPvfr3ckw27bNRp9unTtA5vVHUyeTecQJ3eLZF4xMK'  # Coldkey for authentication
MINER_HOTKEY = '5FTyhanxkXXGYhKL7L5UGTYmUBTk3vPFLJKNZZ9tN2eZ9Zcp'   # Hotkey for operations
SOURCE = '2'  # 2 = X/Twitter data source, 1 = Reddit

# Server configuration
SERVER_PORT = 5000
SERVER_HOST = '0.0.0.0'

# Rate limiting configuration
DAILY_LIMIT_PER_MINER = 20
HOURLY_LIMIT_PER_VALIDATOR = 30
TOTAL_DAILY_LIMIT = 2000

# Path structure
# data/SOURCE/COLDKEY/HOTKEY/filename.parquet