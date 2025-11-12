-- Initial schema for Astro telescope observation system
-- Creates users and observations tables with proper indexes and constraints

-- Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for users table
CREATE INDEX idx_users_user_id ON users(user_id);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active) WHERE is_active = TRUE;

-- Create observations table
CREATE TABLE observations (
    id SERIAL PRIMARY KEY,
    observation_id VARCHAR(255) NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Target information
    target_name VARCHAR(255) NOT NULL,
    observation_object VARCHAR(255) NOT NULL,
    ra DOUBLE PRECISION NOT NULL,
    dec DOUBLE PRECISION NOT NULL,
    
    -- Telescope configuration
    center_frequency DOUBLE PRECISION NOT NULL,
    rf_gain DOUBLE PRECISION NOT NULL,
    if_gain DOUBLE PRECISION NOT NULL,
    bb_gain DOUBLE PRECISION NOT NULL,
    observation_type VARCHAR(100) NOT NULL,
    integration_time DOUBLE PRECISION NOT NULL,
    
    -- Output information
    output_filename VARCHAR(1000) NOT NULL,
    
    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (ra >= 0 AND ra < 360),
    CHECK (dec >= -90 AND dec <= 90),
    CHECK (center_frequency > 0),
    CHECK (integration_time > 0),
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))
);

-- Create indexes for observations table
CREATE INDEX idx_observations_observation_id ON observations(observation_id);
CREATE INDEX idx_observations_user_id ON observations(user_id);
CREATE INDEX idx_observations_status ON observations(status);
CREATE INDEX idx_observations_submitted_at ON observations(submitted_at);
CREATE INDEX idx_observations_target_name ON observations(target_name);

-- Create composite index for common queries
CREATE INDEX idx_observations_user_status ON observations(user_id, status);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_observations_updated_at
    BEFORE UPDATE ON observations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE users IS 'Application users who can submit telescope observations';
COMMENT ON TABLE observations IS 'Telescope observation requests and their configurations';

COMMENT ON COLUMN users.user_id IS 'Unique external user identifier';
COMMENT ON COLUMN users.username IS 'User display name';
COMMENT ON COLUMN users.email IS 'User email address';
COMMENT ON COLUMN users.is_active IS 'Whether the user account is active';

COMMENT ON COLUMN observations.observation_id IS 'Unique observation identifier';
COMMENT ON COLUMN observations.ra IS 'Right Ascension in degrees (0-360)';
COMMENT ON COLUMN observations.dec IS 'Declination in degrees (-90 to 90)';
COMMENT ON COLUMN observations.center_frequency IS 'Center frequency in MHz';
COMMENT ON COLUMN observations.rf_gain IS 'RF gain in dB';
COMMENT ON COLUMN observations.if_gain IS 'IF gain in dB';
COMMENT ON COLUMN observations.bb_gain IS 'Baseband gain in dB';
COMMENT ON COLUMN observations.integration_time IS 'Integration time in seconds';
COMMENT ON COLUMN observations.status IS 'Current observation status: pending, running, completed, failed, cancelled';
