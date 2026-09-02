-- ====================================================================
-- neurotunes_api_keys.sql
-- --------------------------------------------------------------------
-- Additive migration for the NeuroTunes research platform.
-- Creates the API-key table used by the versioned /api/v1 programmatic API
-- for machine-to-machine authentication and per-key rate limiting.
--
-- This is a NEW table only. It does not alter any existing table, so it is
-- safe to apply to the live netraidb (web-core machine, MySQL 8.3):
--
--   mysql -u <user> -p netraidb < dbScripts/neurotunes_api_keys.sql
--
-- Keys are never stored in plaintext: only the SHA-256 hash of the key is
-- persisted. The key_prefix (e.g. "nt_live_a1b2") is stored separately so
-- keys can be identified/managed in a dashboard without exposing the secret.
-- Create keys with:  node server/scripts/create_api_key.js "<label>" [email]
-- ====================================================================

CREATE TABLE IF NOT EXISTS `neurotunes_api_keys` (
  `id` int NOT NULL AUTO_INCREMENT,
  `api_key_hash` varchar(64) NOT NULL COMMENT 'SHA-256 hex of the full API key',
  `key_prefix` varchar(16) NOT NULL COMMENT 'Non-secret identifier prefix, e.g. nt_live_a1b2',
  `name` varchar(120) DEFAULT NULL COMMENT 'Human label / owning project',
  `owner_email` varchar(255) DEFAULT NULL,
  `scopes` varchar(255) DEFAULT 'generate,feedback,sessions,read' COMMENT 'Comma-separated scopes',
  `rate_limit_per_min` int DEFAULT '60' COMMENT 'Max requests per minute for this key',
  `active` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `last_used_at` timestamp NULL DEFAULT NULL,
  `request_count` bigint DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_api_key_hash` (`api_key_hash`),
  KEY `idx_key_prefix` (`key_prefix`),
  KEY `idx_active` (`active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
