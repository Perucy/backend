-- Find which user has this Whoop account
SELECT user_id, email FROM users WHERE whoop_user_id = '13914515';

-- Unlink the Whoop account (set to NULL)
UPDATE users SET whoop_user_id = NULL WHERE whoop_user_id = '13914515';

-- Delete any OAuth tokens for that connection
DELETE FROM oauth_tokens WHERE user_id = '6442286c-8851-4571-bc4a-c2b3b399c7e4' AND provider_name = 'whoop';