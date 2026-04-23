CREATE DATABASE IF NOT EXISTS `paperchat`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `paperchat`;

SET NAMES utf8mb4;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `paperchat_conversation_realtime_events`;
DROP TABLE IF EXISTS `paperchat_conversation_guidance_snapshots`;
DROP TABLE IF EXISTS `paperchat_messages`;
DROP TABLE IF EXISTS `paperchat_conversations`;
DROP TABLE IF EXISTS `paperchat_research_tasks`;
DROP TABLE IF EXISTS `paperchat_knowledge_files`;
DROP TABLE IF EXISTS `paperchat_chat_sessions`;
DROP TABLE IF EXISTS `paperchat_workspaces`;
DROP TABLE IF EXISTS `paperchat_inbox_conversations`;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE IF NOT EXISTS `paperchat_users` (
  `id` VARCHAR(36) NOT NULL,
  `email` VARCHAR(255) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `display_name` VARCHAR(128) NOT NULL,
  `avatar_url` VARCHAR(512) NOT NULL DEFAULT '',
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_users_email` (`email`),
  KEY `idx_paperchat_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_user_sessions` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `refresh_token_hash` VARCHAR(255) NOT NULL,
  `expires_at` DATETIME NOT NULL,
  `revoked_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_user_sessions_user_id` (`user_id`),
  CONSTRAINT `fk_paperchat_user_sessions_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_conversations` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `title_finalized` BOOLEAN NOT NULL DEFAULT FALSE,
  `completed_turn_count` INT NOT NULL DEFAULT 0,
  `last_message_preview` TEXT NOT NULL,
  `last_message_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_conversations_user_id` (`user_id`),
  KEY `idx_paperchat_conversations_last_message_at` (`last_message_at`),
  CONSTRAINT `fk_paperchat_conversations_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_messages` (
  `id` VARCHAR(36) NOT NULL,
  `conversation_id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) DEFAULT NULL,
  `role` VARCHAR(16) NOT NULL,
  `message_type` VARCHAR(32) NOT NULL DEFAULT 'chat',
  `content` TEXT NOT NULL,
  `metadata_json` JSON NOT NULL,
  `citations_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_messages_conversation_id` (`conversation_id`),
  KEY `idx_paperchat_messages_user_id` (`user_id`),
  KEY `idx_paperchat_messages_created_at` (`created_at`),
  CONSTRAINT `fk_paperchat_messages_conversation_id`
    FOREIGN KEY (`conversation_id`) REFERENCES `paperchat_conversations` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_messages_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_conversation_guidance_snapshots` (
  `conversation_id` VARCHAR(36) NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'casual_chat',
  `headline` TEXT NOT NULL,
  `sections_json` JSON NOT NULL,
  `draft_json` JSON DEFAULT NULL,
  `source_message_id` VARCHAR(36) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`conversation_id`),
  CONSTRAINT `fk_paperchat_guidance_conversation_id`
    FOREIGN KEY (`conversation_id`) REFERENCES `paperchat_conversations` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_conversation_realtime_events` (
  `id` VARCHAR(36) NOT NULL,
  `conversation_id` VARCHAR(36) NOT NULL,
  `event_type` VARCHAR(64) NOT NULL,
  `payload_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_realtime_events_conversation_id` (`conversation_id`),
  KEY `idx_paperchat_realtime_events_event_type` (`event_type`),
  KEY `idx_paperchat_realtime_events_created_at` (`created_at`),
  CONSTRAINT `fk_paperchat_realtime_events_conversation_id`
    FOREIGN KEY (`conversation_id`) REFERENCES `paperchat_conversations` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
