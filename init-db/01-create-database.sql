-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create users table (matches your Python User model)
CREATE TABLE users (
    user_id VARCHAR(36) PRIMARY KEY,  -- App provides UUID as string
    email VARCHAR(256) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    
    -- Profile information (optional)
    username VARCHAR(50) UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    display_name VARCHAR(150),
    date_of_birth DATE,
    
    -- Privacy settings
    profile_visibility VARCHAR(20) DEFAULT 'private',
    show_real_name BOOLEAN DEFAULT FALSE,
    show_last_name BOOLEAN DEFAULT FALSE,
    
    -- OAuth provider user IDs
    whoop_user_id VARCHAR(255) UNIQUE,
    spotify_user_id VARCHAR(255) UNIQUE,
    fitbit_user_id VARCHAR(255) UNIQUE,
    
    -- App metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    subscription_tier VARCHAR(20) DEFAULT 'free'
);

-- Create OAuth tokens table
CREATE TABLE oauth_tokens (
    token_id VARCHAR(36) PRIMARY KEY,  -- App provides UUID as string
    user_id VARCHAR(36) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    provider_name VARCHAR(50) NOT NULL,
    
    -- Encrypted token data
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,
    expires_at TIMESTAMPTZ,
    
    -- Token metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one token per user per provider
    UNIQUE(user_id, provider_name)
);

-- Create OAuth states table (for PostgreSQL-based OAuth flow)
CREATE TABLE oauth_states (
    state VARCHAR(255) PRIMARY KEY,
    provider_name VARCHAR(50) NOT NULL,
    fitpro_user_id VARCHAR(36) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    code_verifier TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    extra_data TEXT  -- JSON string for additional data
);

-- Create indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username) WHERE username IS NOT NULL;
CREATE INDEX idx_users_whoop_id ON users(whoop_user_id) WHERE whoop_user_id IS NOT NULL;
CREATE INDEX idx_users_spotify_id ON users(spotify_user_id) WHERE spotify_user_id IS NOT NULL;

CREATE INDEX idx_oauth_tokens_user_provider ON oauth_tokens(user_id, provider_name);
CREATE INDEX idx_oauth_tokens_expires_at ON oauth_tokens(expires_at);
CREATE INDEX idx_oauth_tokens_user_id ON oauth_tokens(user_id);

CREATE INDEX idx_oauth_states_expires_at ON oauth_states(expires_at);
CREATE INDEX idx_oauth_states_user_id ON oauth_states(fitpro_user_id);

-- Create function to update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_oauth_tokens_updated_at BEFORE UPDATE ON oauth_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add some useful constraints
ALTER TABLE oauth_states ADD CONSTRAINT oauth_states_expires_future 
    CHECK (expires_at > created_at);

ALTER TABLE oauth_tokens ADD CONSTRAINT oauth_tokens_provider_valid 
    CHECK (provider_name IN ('whoop', 'spotify'));

ALTER TABLE users ADD CONSTRAINT users_profile_visibility_valid 
    CHECK (profile_visibility IN ('private', 'friends', 'public'));

ALTER TABLE users ADD CONSTRAINT users_subscription_tier_valid 
    CHECK (subscription_tier IN ('free', 'pro'));