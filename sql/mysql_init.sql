CREATE DATABASE IF NOT EXISTS `paperchat`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `paperchat`;

SET NAMES utf8mb4;

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

CREATE TABLE IF NOT EXISTS `paperchat_inbox_conversations` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `title` VARCHAR(255) NOT NULL DEFAULT '默认收件箱会话',
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `summary` TEXT NOT NULL,
  `last_message_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_inbox_conversations_user_id` (`user_id`),
  KEY `idx_paperchat_inbox_conversations_user_id` (`user_id`),
  CONSTRAINT `fk_paperchat_inbox_conversations_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_workspaces` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `share_token` VARCHAR(255) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_workspaces_share_token` (`share_token`),
  KEY `idx_paperchat_workspaces_user_id` (`user_id`),
  KEY `idx_paperchat_workspaces_name` (`name`),
  CONSTRAINT `fk_paperchat_workspaces_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_chat_sessions` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `scope` VARCHAR(32) NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `workspace_id` VARCHAR(36) DEFAULT NULL,
  `inbox_conversation_id` VARCHAR(36) DEFAULT NULL,
  `memory_summary_text` TEXT DEFAULT NULL,
  `last_summarized_message_id` VARCHAR(36) DEFAULT NULL,
  `last_message_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_chat_sessions_user_id` (`user_id`),
  KEY `idx_paperchat_chat_sessions_workspace_id` (`workspace_id`),
  KEY `idx_paperchat_chat_sessions_inbox_id` (`inbox_conversation_id`),
  CONSTRAINT `fk_paperchat_chat_sessions_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_chat_sessions_workspace_id`
    FOREIGN KEY (`workspace_id`) REFERENCES `paperchat_workspaces` (`id`)
    ON DELETE SET NULL,
  CONSTRAINT `fk_paperchat_chat_sessions_inbox_id`
    FOREIGN KEY (`inbox_conversation_id`) REFERENCES `paperchat_inbox_conversations` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_messages` (
  `id` VARCHAR(36) NOT NULL,
  `session_id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) DEFAULT NULL,
  `role` VARCHAR(16) NOT NULL,
  `message_type` VARCHAR(32) NOT NULL DEFAULT 'chat',
  `content` TEXT NOT NULL,
  `metadata_json` JSON NOT NULL,
  `citations_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_messages_session_id` (`session_id`),
  KEY `idx_paperchat_messages_user_id` (`user_id`),
  KEY `idx_paperchat_messages_created_at` (`created_at`),
  CONSTRAINT `fk_paperchat_messages_session_id`
    FOREIGN KEY (`session_id`) REFERENCES `paperchat_chat_sessions` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_messages_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_research_tasks` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `workspace_id` VARCHAR(36) NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'queued',
  `current_node` VARCHAR(64) DEFAULT NULL,
  `progress_percent` FLOAT NOT NULL DEFAULT 0,
  `detail` TEXT NOT NULL,
  `payload_json` JSON DEFAULT NULL,
  `checkpoint_json` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_research_tasks_user_id` (`user_id`),
  KEY `idx_paperchat_research_tasks_workspace_id` (`workspace_id`),
  CONSTRAINT `fk_paperchat_research_tasks_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_research_tasks_workspace_id`
    FOREIGN KEY (`workspace_id`) REFERENCES `paperchat_workspaces` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_knowledge_files` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `workspace_id` VARCHAR(36) DEFAULT NULL,
  `source_type` VARCHAR(32) NOT NULL,
  `title` VARCHAR(512) NOT NULL,
  `source_url` VARCHAR(1024) DEFAULT NULL,
  `object_key` VARCHAR(512) DEFAULT NULL,
  `parser_status` VARCHAR(32) NOT NULL DEFAULT 'uploaded',
  `index_status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `metadata_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_knowledge_files_user_id` (`user_id`),
  KEY `idx_paperchat_knowledge_files_workspace_id` (`workspace_id`),
  CONSTRAINT `fk_paperchat_knowledge_files_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_knowledge_files_workspace_id`
    FOREIGN KEY (`workspace_id`) REFERENCES `paperchat_workspaces` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
