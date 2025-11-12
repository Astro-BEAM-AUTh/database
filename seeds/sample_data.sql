-- Example seed data for development/testing
-- This is optional and should not be run in production

-- Insert test users
INSERT INTO users (user_id, username, email) VALUES
    ('user_001', 'alice_astro', 'alice@example.com'),
    ('user_002', 'bob_observer', 'bob@example.com'),
    ('user_003', 'carol_telescope', 'carol@example.com')
ON CONFLICT (user_id) DO NOTHING;

-- Insert test observations
INSERT INTO observations (
    observation_id, user_id, target_name, observation_object,
    ra, dec, center_frequency, rf_gain, if_gain, bb_gain,
    observation_type, integration_time, output_filename, status
)
SELECT
    'obs_001',
    u.id,
    'M31',
    'Andromeda Galaxy',
    10.68470833,
    41.26875,
    1420.0,
    30.0,
    20.0,
    10.0,
    'imaging',
    600.0,
    'm31_observation.fits',
    'completed'
FROM users u WHERE u.username = 'alice_astro'
ON CONFLICT (observation_id) DO NOTHING;

INSERT INTO observations (
    observation_id, user_id, target_name, observation_object,
    ra, dec, center_frequency, rf_gain, if_gain, bb_gain,
    observation_type, integration_time, output_filename, status
)
SELECT
    'obs_002',
    u.id,
    'M42',
    'Orion Nebula',
    83.82208333,
    -5.39111111,
    1420.0,
    30.0,
    20.0,
    10.0,
    'spectroscopy',
    1200.0,
    'm42_observation.fits',
    'pending'
FROM users u WHERE u.username = 'bob_observer'
ON CONFLICT (observation_id) DO NOTHING;
