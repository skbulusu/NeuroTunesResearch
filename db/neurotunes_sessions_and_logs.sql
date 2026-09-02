-- ====================================================================
-- neurotunes_sessions_and_logs.sql
-- --------------------------------------------------------------------
-- Additive migration: creates neurotunes_music_sessions and
-- neurotunes_generation_log (both referenced by /api/v1 but missing
-- from the live DB). Safe to apply — no ALTER, no DROP.
--
-- Apply:
--   mysql -u <user> -p netraidb < neurotunes_sessions_and_logs.sql
-- or inside docker:
--   docker exec -i netrai-db mysql -u <user> -p netraidb < neurotunes_sessions_and_logs.sql
-- ====================================================================

CREATE TABLE IF NOT EXISTS `neurotunes_music_sessions` (
  `session_id` varchar(36) NOT NULL,
  `user_id` int DEFAULT NULL,
  `user_name` varchar(80) DEFAULT NULL,
  `session_name` varchar(100) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` timestamp NULL DEFAULT NULL,
  `session_notes` text,
  PRIMARY KEY (`session_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_user_name` (`user_name`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_session_user_created` (`user_id`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `neurotunes_generation_log` (
  `log_id` int NOT NULL AUTO_INCREMENT,
  `session_id` varchar(36) DEFAULT NULL,
  `user_id` int DEFAULT NULL,
  `user_name` varchar(80) DEFAULT NULL,
  `age` int DEFAULT NULL,
  `gender` varchar(20) DEFAULT NULL,
  `primary_diagnosis` varchar(100) DEFAULT NULL,
  `therapy_goal` varchar(50) DEFAULT NULL,
  `current_mood` varchar(50) DEFAULT NULL,
  `stress_level` int DEFAULT NULL,
  `sleep_quality` int DEFAULT NULL,
  `energy_level` int DEFAULT NULL,
  `patient_state` text COMMENT 'JSON array: [valence, arousal, cognitive_load, motor_impairment]',
  `music_params` text COMMENT 'JSON: tempo, key, mode, rhythm_stability, etc.',
  `track_id` varchar(100) DEFAULT NULL,
  `midi_filename` varchar(255) DEFAULT NULL,
  `audio_filename` varchar(255) DEFAULT NULL,
  `binaural_frequency` float DEFAULT NULL,
  `generation_timestamp` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `model_version` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`log_id`),
  KEY `idx_session_id` (`session_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_user_name` (`user_name`),
  KEY `idx_generation_timestamp` (`generation_timestamp`),
  KEY `idx_therapy_goal` (`therapy_goal`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- RLHF feedback for generated tracks. Referenced by /api/v1/feedback.
-- generation_log_id points at neurotunes_generation_log.log_id (FK omitted
-- deliberately to keep this migration additive/standalone; the app validates
-- the reference before inserting).
CREATE TABLE IF NOT EXISTS `neurotunes_feedback_log` (
  `feedback_id` int NOT NULL AUTO_INCREMENT,
  `generation_log_id` int NOT NULL,
  `user_id` int DEFAULT NULL,
  `user_name` varchar(80) DEFAULT NULL,
  `feedback_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `overall_rating` int DEFAULT NULL,
  `effectiveness_rating` int DEFAULT NULL,
  `enjoyment_rating` int DEFAULT NULL,
  `reported_feeling` varchar(50) DEFAULT NULL,
  `mood_change` enum('much_better','better','same','worse','much_worse') DEFAULT NULL,
  `energy_change` enum('much_higher','higher','same','lower','much_lower') DEFAULT NULL,
  `stress_change` enum('much_less','less','same','more','much_more') DEFAULT NULL,
  `feedback_text` text,
  `listen_duration_seconds` int DEFAULT NULL,
  `replay_count` int DEFAULT '0',
  `skipped_early` tinyint(1) DEFAULT '0',
  `symptom_improvement` enum('significant','moderate','slight','none','worse') DEFAULT NULL,
  `would_use_again` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`feedback_id`),
  KEY `idx_generation_log_id` (`generation_log_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_user_name` (`user_name`),
  KEY `idx_feedback_time` (`feedback_time`),
  KEY `idx_overall_rating` (`overall_rating`),
  KEY `idx_mood_change` (`mood_change`),
  KEY `idx_feedback_rating_time` (`overall_rating`,`feedback_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

