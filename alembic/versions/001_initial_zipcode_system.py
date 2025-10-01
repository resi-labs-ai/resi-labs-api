"""Initial zipcode assignment system

Revision ID: 001_initial_zipcode_system
Revises: 
Create Date: 2024-09-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_zipcode_system'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM types
    op.execute("CREATE TYPE epoch_status_enum AS ENUM ('pending', 'active', 'completed', 'archived')")
    op.execute("CREATE TYPE market_tier_enum AS ENUM ('premium', 'standard', 'emerging')")
    op.execute("CREATE TYPE validation_status_enum AS ENUM ('in_progress', 'completed', 'failed')")
    op.execute("CREATE TYPE validation_result_enum AS ENUM ('pass', 'fail', 'partial')")
    op.execute("CREATE TYPE validation_type_enum AS ENUM ('basic', 'spot_check', 'full')")
    op.execute("CREATE TYPE submission_status_enum AS ENUM ('in_progress', 'completed', 'failed')")

    # Create zipcodes table
    op.create_table('zipcodes',
        sa.Column('zipcode', sa.String(length=10), nullable=False),
        sa.Column('state', sa.String(length=2), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('county', sa.String(length=100), nullable=True),
        sa.Column('geographic_region', sa.String(length=50), nullable=True),
        sa.Column('population', sa.Integer(), nullable=True),
        sa.Column('median_home_value', sa.Integer(), nullable=True),
        sa.Column('expected_listings', sa.Integer(), nullable=False),
        sa.Column('market_tier', postgresql.ENUM('premium', 'standard', 'emerging', name='market_tier_enum'), nullable=False),
        sa.Column('last_assigned', sa.DateTime(timezone=True), nullable=True),
        sa.Column('assignment_count', sa.Integer(), nullable=True, default=0),
        sa.Column('base_selection_weight', sa.Float(), nullable=True, default=1.0),
        sa.Column('data_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('data_source', sa.String(length=50), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_honeypot', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('zipcode', name=op.f('pk_zipcodes'))
    )
    op.create_index('ix_zipcodes_state', 'zipcodes', ['state'], unique=False)
    op.create_index('ix_zipcodes_market_tier', 'zipcodes', ['market_tier'], unique=False)
    op.create_index('ix_zipcodes_expected_listings', 'zipcodes', ['expected_listings'], unique=False)
    op.create_index('ix_zipcodes_last_assigned', 'zipcodes', ['last_assigned'], unique=False)
    op.create_index('ix_zipcodes_is_active', 'zipcodes', ['is_active'], unique=False)
    op.create_index('ix_zipcodes_state_tier', 'zipcodes', ['state', 'market_tier'], unique=False)
    op.create_index('ix_zipcodes_selection_weight', 'zipcodes', ['base_selection_weight'], unique=False)

    # Create epochs table
    op.create_table('epochs',
        sa.Column('id', sa.String(length=20), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('nonce', sa.String(length=64), nullable=False),
        sa.Column('target_listings', sa.Integer(), nullable=False),
        sa.Column('tolerance_percent', sa.Integer(), nullable=False, default=10),
        sa.Column('status', postgresql.ENUM('pending', 'active', 'completed', 'archived', name='epoch_status_enum'), nullable=False, default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('selection_seed', sa.Integer(), nullable=True),
        sa.Column('algorithm_version', sa.String(length=10), nullable=True, default='v1.0'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_epochs')),
        sa.UniqueConstraint('nonce', name=op.f('uq_epochs_nonce'))
    )
    op.create_index('ix_epochs_start_time', 'epochs', ['start_time'], unique=False)
    op.create_index('ix_epochs_status', 'epochs', ['status'], unique=False)
    op.create_index('ix_epochs_created_at', 'epochs', ['created_at'], unique=False)

    # Create epoch_assignments table
    op.create_table('epoch_assignments',
        sa.Column('epoch_id', sa.String(length=20), nullable=False),
        sa.Column('zipcode', sa.String(length=10), nullable=False),
        sa.Column('expected_listings', sa.Integer(), nullable=False),
        sa.Column('state', sa.String(length=2), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('county', sa.String(length=100), nullable=True),
        sa.Column('market_tier', postgresql.ENUM('premium', 'standard', 'emerging', name='market_tier_enum'), nullable=False),
        sa.Column('selection_weight', sa.Float(), nullable=True),
        sa.Column('geographic_region', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['epoch_id'], ['epochs.id'], name=op.f('fk_epoch_assignments_epoch_id_epochs'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('epoch_id', 'zipcode', name=op.f('pk_epoch_assignments'))
    )
    op.create_index('ix_epoch_assignments_epoch_id', 'epoch_assignments', ['epoch_id'], unique=False)
    op.create_index('ix_epoch_assignments_zipcode', 'epoch_assignments', ['zipcode'], unique=False)
    op.create_index('ix_epoch_assignments_state', 'epoch_assignments', ['state'], unique=False)
    op.create_index('ix_epoch_assignments_market_tier', 'epoch_assignments', ['market_tier'], unique=False)

    # Create validator_results table
    op.create_table('validator_results',
        sa.Column('epoch_id', sa.String(length=20), nullable=False),
        sa.Column('validator_hotkey', sa.String(length=100), nullable=False),
        sa.Column('validation_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('validation_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('miners_evaluated', sa.Integer(), nullable=False),
        sa.Column('total_validated_listings', sa.Integer(), nullable=True),
        sa.Column('top_3_miners', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('s3_upload_complete', sa.Boolean(), nullable=True, default=False),
        sa.Column('s3_upload_path', sa.String(length=500), nullable=True),
        sa.Column('s3_upload_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('validation_status', postgresql.ENUM('in_progress', 'completed', 'failed', name='validation_status_enum'), nullable=False, default='in_progress'),
        sa.Column('validation_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['epoch_id'], ['epochs.id'], name=op.f('fk_validator_results_epoch_id_epochs'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('epoch_id', 'validator_hotkey', name=op.f('pk_validator_results'))
    )
    op.create_index('ix_validator_results_epoch_id', 'validator_results', ['epoch_id'], unique=False)
    op.create_index('ix_validator_results_validator_hotkey', 'validator_results', ['validator_hotkey'], unique=False)
    op.create_index('ix_validator_results_validation_timestamp', 'validator_results', ['validation_timestamp'], unique=False)
    op.create_index('ix_validator_results_validation_status', 'validator_results', ['validation_status'], unique=False)
    op.create_index('ix_validator_results_s3_upload_complete', 'validator_results', ['s3_upload_complete'], unique=False)

    # Create validation_audit table
    op.create_table('validation_audit',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('epoch_id', sa.String(length=20), nullable=False),
        sa.Column('validator_hotkey', sa.String(length=100), nullable=False),
        sa.Column('miner_hotkey', sa.String(length=100), nullable=False),
        sa.Column('zipcode', sa.String(length=10), nullable=True),
        sa.Column('validation_type', postgresql.ENUM('basic', 'spot_check', 'full', name='validation_type_enum'), nullable=False),
        sa.Column('validation_result', postgresql.ENUM('pass', 'fail', 'partial', name='validation_result_enum'), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('listings_checked', sa.Integer(), nullable=True),
        sa.Column('issues_found', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['epoch_id'], ['epochs.id'], name=op.f('fk_validation_audit_epoch_id_epochs'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_validation_audit'))
    )
    op.create_index('ix_validation_audit_epoch_validator', 'validation_audit', ['epoch_id', 'validator_hotkey'], unique=False)
    op.create_index('ix_validation_audit_epoch_miner', 'validation_audit', ['epoch_id', 'miner_hotkey'], unique=False)
    op.create_index('ix_validation_audit_validation_result', 'validation_audit', ['validation_result'], unique=False)
    op.create_index('ix_validation_audit_validation_type', 'validation_audit', ['validation_type'], unique=False)
    op.create_index('ix_validation_audit_timestamp', 'validation_audit', ['validation_timestamp'], unique=False)
    op.create_index('ix_validation_audit_zipcode', 'validation_audit', ['zipcode'], unique=False)

    # Create miner_submissions table (optional)
    op.create_table('miner_submissions',
        sa.Column('epoch_id', sa.String(length=20), nullable=False),
        sa.Column('miner_hotkey', sa.String(length=100), nullable=False),
        sa.Column('submission_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('listings_scraped', sa.Integer(), nullable=True),
        sa.Column('zipcodes_completed', sa.Integer(), nullable=True),
        sa.Column('s3_upload_complete', sa.Boolean(), nullable=True, default=False),
        sa.Column('s3_upload_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', postgresql.ENUM('in_progress', 'completed', 'failed', name='submission_status_enum'), nullable=True, default='in_progress'),
        sa.Column('scraping_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['epoch_id'], ['epochs.id'], name=op.f('fk_miner_submissions_epoch_id_epochs'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('epoch_id', 'miner_hotkey', name=op.f('pk_miner_submissions'))
    )
    op.create_index('ix_miner_submissions_epoch_id', 'miner_submissions', ['epoch_id'], unique=False)
    op.create_index('ix_miner_submissions_miner_hotkey', 'miner_submissions', ['miner_hotkey'], unique=False)
    op.create_index('ix_miner_submissions_submission_timestamp', 'miner_submissions', ['submission_timestamp'], unique=False)
    op.create_index('ix_miner_submissions_status', 'miner_submissions', ['status'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('miner_submissions')
    op.drop_table('validation_audit')
    op.drop_table('validator_results')
    op.drop_table('epoch_assignments')
    op.drop_table('epochs')
    op.drop_table('zipcodes')
    
    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS submission_status_enum")
    op.execute("DROP TYPE IF EXISTS validation_type_enum")
    op.execute("DROP TYPE IF EXISTS validation_result_enum")
    op.execute("DROP TYPE IF EXISTS validation_status_enum")
    op.execute("DROP TYPE IF EXISTS market_tier_enum")
    op.execute("DROP TYPE IF EXISTS epoch_status_enum")
