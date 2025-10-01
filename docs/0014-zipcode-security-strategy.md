# Zipcode Assignment Security Strategy

## Security Challenge

Since the API server code will be public, miners could potentially:
1. **Predict future zipcode assignments** by analyzing the selection algorithm
2. **Pre-scrape popular zipcodes** before they're officially assigned
3. **Game the system** by preparing data in advance

## Multi-Layer Security Approach

### **Layer 1: Deterministic but Unpredictable Selection**

**Implementation**: Seed-based randomization that appears random but is deterministic for validation

```python
def generate_epoch_seed(epoch_id: str, secret_key: str) -> int:
    """Generate deterministic but unpredictable seed for zipcode selection"""
    seed_string = f"{epoch_id}:{secret_key}:{datetime.utcnow().strftime('%Y-%m-%d')}"
    return int(hashlib.sha256(seed_string.encode()).hexdigest()[:8], 16)

def select_zipcodes_with_seed(eligible_zipcodes: List[Zipcode], target_listings: int, seed: int) -> List[Zipcode]:
    """Select zipcodes using seeded randomization"""
    random.seed(seed)
    
    # Weighted selection based on:
    # - Expected listings (primary factor)
    # - Market tier weights (premium=1.5, standard=1.0, emerging=0.8)
    # - State priority (PA=1, NJ=2, etc.)
    # - Cooldown factor (recently assigned = lower weight)
    
    weights = []
    for zipcode in eligible_zipcodes:
        base_weight = zipcode.expected_listings
        tier_weight = MARKET_TIER_WEIGHTS[zipcode.market_tier]
        state_weight = 1.0 / STATE_PRIORITIES[zipcode.state]  # Lower number = higher priority
        cooldown_weight = calculate_cooldown_weight(zipcode.last_assigned)
        
        final_weight = base_weight * tier_weight * state_weight * cooldown_weight
        weights.append(final_weight)
    
    # Random weighted selection to hit target ± tolerance
    selected = random.choices(eligible_zipcodes, weights=weights, k=calculate_zipcode_count(target_listings))
    return selected
```

**Security Benefits**:
- ✅ **Unpredictable**: Miners can't predict future assignments without the secret key
- ✅ **Deterministic**: All validators get identical results for validation
- ✅ **Fair**: Still uses proper weighting for market coverage

### **Layer 2: Epoch-Specific Nonces (Already Planned)**

**Implementation**: Each epoch gets a unique nonce that miners must include in S3 uploads

```python
def generate_epoch_nonce(epoch_id: str, secret_key: str, selected_zipcodes: List[str]) -> str:
    """Generate epoch-specific nonce to prevent pre-scraping"""
    zipcode_hash = hashlib.sha256(''.join(sorted(selected_zipcodes)).encode()).hexdigest()
    nonce_input = f"{epoch_id}:{secret_key}:{zipcode_hash}"
    return hashlib.sha256(nonce_input.encode()).hexdigest()[:16]
```

**Security Benefits**:
- ✅ **Prevents Pre-scraping**: Data without correct nonce is invalid
- ✅ **Epoch-Specific**: Each 4-hour period has unique nonce
- ✅ **Tamper-Proof**: Nonce tied to exact zipcode selection

### **Layer 3: Just-In-Time Assignment Revelation**

**Implementation**: Assignments become visible only at epoch start, not in advance

```python
class EpochManager:
    def get_current_assignments(self) -> Optional[EpochAssignment]:
        """Only return assignments for current active epoch"""
        now = datetime.utcnow()
        current_epoch = self.get_epoch_for_timestamp(now)
        
        # Only reveal if epoch has started (not pre-generated)
        if now >= current_epoch.start_time:
            return current_epoch
        else:
            return None  # Future epochs not revealed
    
    def pre_generate_next_epoch(self) -> None:
        """Generate next epoch 5 minutes before start (internal only)"""
        # This runs as background task but doesn't expose via API
        next_epoch = self.create_epoch_assignment(
            start_time=self.get_next_epoch_start(),
            secret_seed=self.generate_epoch_seed()
        )
        # Store in database but don't expose via API until start_time
```

**Security Benefits**:
- ✅ **No Future Visibility**: Miners can't see upcoming assignments
- ✅ **Minimal Lead Time**: Only 5-minute internal pre-generation
- ✅ **Atomic Revelation**: All miners get assignments simultaneously

### **Layer 4: Dynamic Algorithm Parameters**

**Implementation**: Make selection algorithm parameters configurable and adjustable

```python
# Environment variables that can be changed without code updates
MARKET_TIER_WEIGHTS = {
    "premium": float(os.getenv("PREMIUM_WEIGHT", "1.5")),
    "standard": float(os.getenv("STANDARD_WEIGHT", "1.0")), 
    "emerging": float(os.getenv("EMERGING_WEIGHT", "0.8"))
}

STATE_PRIORITIES = parse_state_priorities(os.getenv("STATE_PRIORITIES", "PA:1,NJ:2,NY:3"))

# Algorithm variation parameters
SELECTION_RANDOMNESS = float(os.getenv("SELECTION_RANDOMNESS", "0.3"))  # 0=pure weighted, 1=pure random
GEOGRAPHIC_SPREAD_FACTOR = float(os.getenv("GEOGRAPHIC_SPREAD", "0.2"))  # Encourage geographic diversity
```

**Security Benefits**:
- ✅ **Adaptable**: Can adjust parameters if gaming detected
- ✅ **Unpredictable**: Algorithm behavior can evolve
- ✅ **No Code Changes**: Adjustments via environment variables

### **Layer 5: Honeypot Detection**

**Implementation**: Include decoy zipcodes to detect pre-scraping attempts

```python
def add_honeypot_zipcodes(assignments: List[Zipcode]) -> List[Zipcode]:
    """Add 1-2 decoy zipcodes that shouldn't have data"""
    if random.random() < 0.3:  # 30% chance to include honeypot
        honeypot = create_honeypot_zipcode()  # Very low activity zipcode
        assignments.append(honeypot)
        logger.info(f"Added honeypot zipcode {honeypot.zipcode} to epoch")
    return assignments

def validate_miner_submission(submission: MinerSubmission) -> ValidationResult:
    """Check for honeypot violations during validation"""
    honeypots = get_honeypot_zipcodes(submission.epoch_id)
    
    for honeypot in honeypots:
        if honeypot.zipcode in submission.zipcodes:
            honeypot_data = submission.get_zipcode_data(honeypot.zipcode)
            if len(honeypot_data) > HONEYPOT_THRESHOLD:  # e.g., >50 listings
                return ValidationResult(
                    valid=False,
                    reason=f"Suspicious data volume for low-activity zipcode {honeypot.zipcode}",
                    penalty=True
                )
    
    return ValidationResult(valid=True)
```

**Security Benefits**:
- ✅ **Gaming Detection**: Identifies miners with pre-scraped data
- ✅ **Automatic Penalties**: Invalid submissions get zero rewards
- ✅ **Adaptive**: Can adjust honeypot frequency and thresholds

## Implementation Priority

### **Phase 1 (Week 1-2): Core Security**
- ✅ Seed-based deterministic selection
- ✅ Epoch-specific nonces
- ✅ Just-in-time revelation

### **Phase 2 (Week 3): Enhanced Security**
- ✅ Dynamic algorithm parameters
- ✅ Honeypot detection system

### **Phase 3 (Post-Launch): Monitoring**
- ✅ Gaming detection analytics
- ✅ Algorithm effectiveness monitoring
- ✅ Parameter tuning based on behavior

## Configuration Example

```bash
# Security Configuration (.env.production)
ZIPCODE_SECRET_KEY=your-32-char-minimum-secret-key-here
SELECTION_RANDOMNESS=0.25
GEOGRAPHIC_SPREAD_FACTOR=0.15
HONEYPOT_PROBABILITY=0.3
HONEYPOT_THRESHOLD=50

# Market Weights (adjustable for gaming mitigation)
PREMIUM_WEIGHT=1.5
STANDARD_WEIGHT=1.0
EMERGING_WEIGHT=0.8

# State Priorities (you control this ordering)
STATE_PRIORITIES=PA:1,NJ:2,NY:3,DE:4,MD:5
```

## Monitoring & Detection

### **Gaming Detection Metrics**
```python
# Track suspicious patterns
class GamingDetector:
    def analyze_submission_patterns(self, submissions: List[MinerSubmission]) -> Dict:
        return {
            "early_submissions": self.detect_unusually_fast_submissions(),
            "perfect_predictions": self.detect_perfect_zipcode_coverage(),
            "honeypot_violations": self.detect_honeypot_gaming(),
            "data_quality_anomalies": self.detect_suspicious_data_patterns()
        }
```

### **Alert Thresholds**
- **Submission Speed**: Alert if miner completes >80% of zipcodes in <30 minutes
- **Perfect Coverage**: Alert if miner hits exact target listings multiple epochs
- **Honeypot Hits**: Immediate penalty for excessive honeypot data
- **Pattern Recognition**: ML-based detection of gaming patterns

## Conclusion

This multi-layer approach provides strong protection against gaming while maintaining fairness:

1. **Miners can't predict** future assignments (seeded randomization + secret key)
2. **Pre-scraping is useless** (epoch nonces + just-in-time revelation)  
3. **Gaming is detectable** (honeypots + pattern analysis)
4. **System is adaptable** (configurable parameters + monitoring)

The public code repository won't reveal the secret key or exact parameter values, making the system secure even with full code visibility.
