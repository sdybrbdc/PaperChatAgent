CREATE DATABASE IF NOT EXISTS `paperchatagent`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `paperchatagent`;

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS `users` (
  `id` CHAR(36) NOT NULL,
  `email` VARCHAR(255) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `display_name` VARCHAR(128) NOT NULL,
  `avatar_url` VARCHAR(512) DEFAULT NULL,
  `description` TEXT DEFAULT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_users_email` (`email`),
  KEY `idx_users_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `user_sessions` (
  `id` CHAR(36) NOT NULL,
  `user_id` CHAR(36) NOT NULL,
  `refresh_token_hash` VARCHAR(255) NOT NULL,
  `session_name` VARCHAR(255) DEFAULT NULL,
  `user_agent` VARCHAR(512) DEFAULT NULL,
  `ip_address` VARCHAR(64) DEFAULT NULL,
  `expires_at` DATETIME NOT NULL,
  `last_seen_at` DATETIME DEFAULT NULL,
  `revoked_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_sessions_refresh_token_hash` (`refresh_token_hash`),
  KEY `idx_user_sessions_user_id` (`user_id`),
  KEY `idx_user_sessions_expires_at` (`expires_at`),
  CONSTRAINT `fk_user_sessions_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `inbox_conversations` (
  `id` CHAR(36) NOT NULL,
  `user_id` CHAR(36) NOT NULL,
  `title` VARCHAR(255) NOT NULL DEFAULT '默认收件箱会话',
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `summary` TEXT DEFAULT NULL,
  `last_message_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_inbox_conversations_user_id` (`user_id`),
  KEY `idx_inbox_conversations_last_message_at` (`last_message_at`),
  CONSTRAINT `fk_inbox_conversations_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `research_workspaces` (
  `id` CHAR(36) NOT NULL,
  `user_id` CHAR(36) NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT DEFAULT NULL,
  `origin_inbox_conversation_id` CHAR(36) DEFAULT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `share_token` VARCHAR(128) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_research_workspaces_user_name` (`user_id`, `name`),
  UNIQUE KEY `uk_research_workspaces_share_token` (`share_token`),
  KEY `idx_research_workspaces_origin_inbox` (`origin_inbox_conversation_id`),
  CONSTRAINT `fk_research_workspaces_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_research_workspaces_origin_inbox`
    FOREIGN KEY (`origin_inbox_conversation_id`) REFERENCES `inbox_conversations` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `workspace_share_links` (
  `id` CHAR(36) NOT NULL,
  `workspace_id` CHAR(36) NOT NULL,
  `share_token` VARCHAR(128) NOT NULL,
  `is_enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `expires_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_workspace_share_links_share_token` (`share_token`),
  KEY `idx_workspace_share_links_workspace_id` (`workspace_id`),
  CONSTRAINT `fk_workspace_share_links_workspace_id`
    FOREIGN KEY (`workspace_id`) REFERENCES `research_workspaces` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `chat_sessions` (
  `id` CHAR(36) NOT NULL,
  `user_id` CHAR(36) NOT NULL,
  `workspace_id` CHAR(36) DEFAULT NULL,
  `inbox_conversation_id` CHAR(36) DEFAULT NULL,
  `session_scope` VARCHAR(32) NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `summary` TEXT DEFAULT NULL,
  `last_message_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_chat_sessions_user_id` (`user_id`),
  KEY `idx_chat_sessions_workspace_id` (`workspace_id`),
  KEY `idx_chat_sessions_inbox_conversation_id` (`inbox_conversation_id`),
  KEY `idx_chat_sessions_last_message_at` (`last_message_at`),
  CONSTRAINT `fk_chat_sessions_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_chat_sessions_workspace_id`
    FOREIGN KEY (`workspace_id`) REFERENCES `research_workspaces` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_chat_sessions_inbox_conversation_id`
    FOREIGN KEY (`inbox_conversation_id`) REFERENCES `inbox_conversations` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `chk_chat_sessions_scope`
    CHECK (
      (`session_scope` = 'workspace' AND `workspace_id` IS NOT NULL AND `inbox_conversation_id` IS NULL)
      OR
      (`session_scope` = 'inbox' AND `workspace_id` IS NULL AND `inbox_conversation_id` IS NOT NULL)
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `messages` (
  `id` CHAR(36) NOT NULL,
  `session_id` CHAR(36) NOT NULL,
  `user_id` CHAR(36) DEFAULT NULL,
  `role` VARCHAR(16) NOT NULL,
  `message_type` VARCHAR(32) NOT NULL DEFAULT 'chat',
  `sequence_no` INT NOT NULL,
  `content` LONGTEXT NOT NULL,
  `content_json` JSON DEFAULT NULL,
  `citation_payload` JSON DEFAULT NULL,
  `metadata_json` JSON DEFAULT NULL,
  `input_tokens` INT NOT NULL DEFAULT 0,
  `output_tokens` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_messages_session_seq` (`session_id`, `sequence_no`),
  KEY `idx_messages_session_created` (`session_id`, `created_at`),
  KEY `idx_messages_role` (`role`),
  KEY `idx_messages_message_type` (`message_type`),
  CONSTRAINT `fk_messages_session_id`
    FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_messages_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `knowledge_bases` (
  `id` CHAR(36) NOT NULL,
  `user_id` CHAR(36) NOT NULL,
  `workspace_id` CHAR(36) DEFAULT NULL,
  `scope` VARCHAR(32) NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT DEFAULT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_knowledge_bases_user_id` (`user_id`),
  KEY `idx_knowledge_bases_workspace_id` (`workspace_id`),
  KEY `idx_knowledge_bases_scope` (`scope`),
  CONSTRAINT `fk_knowledge_bases_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_knowledge_bases_workspace_id`
    FOREIGN KEY (`workspace_id`) REFERENCES `research_workspaces` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `chk_knowledge_bases_scope`
    CHECK (
      (`scope` = 'global' AND `workspace_id` IS NULL)
      OR
      (`scope` = 'workspace_private' AND `workspace_id` IS NOT NULL)
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `workspace_knowledge_links` (
  `id` CHAR(36) NOT NULL,
  `workspace_id` CHAR(36) NOT NULL,
  `knowledge_base_id` CHAR(36) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_workspace_knowledge_links` (`workspace_id`, `knowledge_base_id`),
  CONSTRAINT `fk_workspace_knowledge_links_workspace_id`
    FOREIGN KEY (`workspace_id`) REFERENCES `research_workspaces` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_workspace_knowledge_links_knowledge_base_id`
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `knowledge_files` (
  `id` CHAR(36) NOT NULL,
  `knowledge_base_id` CHAR(36) NOT NULL,
  `user_id` CHAR(36) NOT NULL,
  `workspace_id` CHAR(36) DEFAULT NULL,
  `source_type` VARCHAR(32) NOT NULL,
  `title` VARCHAR(512) NOT NULL,
  `source_url` VARCHAR(1024) DEFAULT NULL,
  `external_paper_id` VARCHAR(128) DEFAULT NULL,
  `object_key` VARCHAR(512) DEFAULT NULL,
  `mime_type` VARCHAR(128) DEFAULT NULL,
  `file_size_bytes` BIGINT NOT NULL DEFAULT 0,
  `checksum_sha256` VARCHAR(64) DEFAULT NULL,
  `parser_status` VARCHAR(32) NOT NULL DEFAULT 'uploaded',
  `index_status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `metadata_json` JSON DEFAULT NULL,
  `uploaded_at` DATETIME DEFAULT NULL,
  `parsed_at` DATETIME DEFAULT NULL,
  `indexed_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_knowledge_files_knowledge_base_id` (`knowledge_base_id`),
  KEY `idx_knowledge_files_user_id` (`user_id`),
  KEY `idx_knowledge_files_workspace_id` (`workspace_id`),
  KEY `idx_knowledge_files_external_paper_id` (`external_paper_id`),
  KEY `idx_knowledge_files_parser_status` (`parser_status`),
  KEY `idx_knowledge_files_index_status` (`index_status`),
  CONSTRAINT `fk_knowledge_files_knowledge_base_id`
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_knowledge_files_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_knowledge_files_workspace_id`
    FOREIGN KEY (`workspace_id`) REFERENCES `research_workspaces` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `knowledge_chunks` (
  `id` CHAR(36) NOT NULL,
  `knowledge_file_id` CHAR(36) NOT NULL,
  `chunk_index` INT NOT NULL,
  `page_no` INT DEFAULT NULL,
  `section_title` VARCHAR(512) DEFAULT NULL,
  `content_text` LONGTEXT NOT NULL,
  `content_tokens` INT NOT NULL DEFAULT 0,
  `chunk_hash` VARCHAR(64) DEFAULT NULL,
  `vector_collection` VARCHAR(255) DEFAULT NULL,
  `vector_doc_id` VARCHAR(255) DEFAULT NULL,
  `locator_json` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_knowledge_chunks_file_index` (`knowledge_file_id`, `chunk_index`),
  KEY `idx_knowledge_chunks_chunk_hash` (`chunk_hash`),
  CONSTRAINT `fk_knowledge_chunks_knowledge_file_id`
    FOREIGN KEY (`knowledge_file_id`) REFERENCES `knowledge_files` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `research_tasks` (
  `id` CHAR(36) NOT NULL,
  `user_id` CHAR(36) NOT NULL,
  `workspace_id` CHAR(36) NOT NULL,
  `source_session_id` CHAR(36) DEFAULT NULL,
  `title` VARCHAR(255) NOT NULL,
  `task_type` VARCHAR(64) NOT NULL DEFAULT 'topic_exploration',
  `status` VARCHAR(32) NOT NULL DEFAULT 'queued',
  `current_node` VARCHAR(64) DEFAULT NULL,
  `payload_json` JSON DEFAULT NULL,
  `result_summary` TEXT DEFAULT NULL,
  `progress_percent` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `error_message` TEXT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `started_at` DATETIME DEFAULT NULL,
  `finished_at` DATETIME DEFAULT NULL,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_research_tasks_user_id` (`user_id`),
  KEY `idx_research_tasks_workspace_id` (`workspace_id`),
  KEY `idx_research_tasks_status` (`status`),
  KEY `idx_research_tasks_current_node` (`current_node`),
  CONSTRAINT `fk_research_tasks_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_research_tasks_workspace_id`
    FOREIGN KEY (`workspace_id`) REFERENCES `research_workspaces` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_research_tasks_source_session_id`
    FOREIGN KEY (`source_session_id`) REFERENCES `chat_sessions` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `workflow_runs` (
  `id` CHAR(36) NOT NULL,
  `task_id` CHAR(36) NOT NULL,
  `workflow_name` VARCHAR(128) NOT NULL,
  `workflow_version` VARCHAR(64) DEFAULT NULL,
  `current_node` VARCHAR(64) DEFAULT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'queued',
  `node_statuses_json` JSON DEFAULT NULL,
  `trace_json` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `started_at` DATETIME DEFAULT NULL,
  `finished_at` DATETIME DEFAULT NULL,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_workflow_runs_task_id` (`task_id`),
  KEY `idx_workflow_runs_status` (`status`),
  CONSTRAINT `fk_workflow_runs_task_id`
    FOREIGN KEY (`task_id`) REFERENCES `research_tasks` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `workflow_node_runs` (
  `id` CHAR(36) NOT NULL,
  `workflow_run_id` CHAR(36) NOT NULL,
  `node_name` VARCHAR(128) NOT NULL,
  `node_order` INT NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `input_json` JSON DEFAULT NULL,
  `output_json` JSON DEFAULT NULL,
  `error_message` TEXT DEFAULT NULL,
  `duration_ms` BIGINT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `started_at` DATETIME DEFAULT NULL,
  `finished_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_workflow_node_runs_run_order` (`workflow_run_id`, `node_order`),
  KEY `idx_workflow_node_runs_node_name` (`node_name`),
  KEY `idx_workflow_node_runs_status` (`status`),
  CONSTRAINT `fk_workflow_node_runs_workflow_run_id`
    FOREIGN KEY (`workflow_run_id`) REFERENCES `workflow_runs` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `research_papers` (
  `id` CHAR(36) NOT NULL,
  `task_id` CHAR(36) NOT NULL,
  `workspace_id` CHAR(36) NOT NULL,
  `knowledge_file_id` CHAR(36) DEFAULT NULL,
  `source_type` VARCHAR(32) NOT NULL,
  `paper_identifier` VARCHAR(128) DEFAULT NULL,
  `title` VARCHAR(1024) NOT NULL,
  `abstract_text` LONGTEXT DEFAULT NULL,
  `authors_json` JSON DEFAULT NULL,
  `published_at` DATETIME DEFAULT NULL,
  `categories_json` JSON DEFAULT NULL,
  `paper_url` VARCHAR(1024) DEFAULT NULL,
  `pdf_url` VARCHAR(1024) DEFAULT NULL,
  `selection_status` VARCHAR(32) NOT NULL DEFAULT 'selected',
  `metadata_json` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_research_papers_task_id` (`task_id`),
  KEY `idx_research_papers_workspace_id` (`workspace_id`),
  KEY `idx_research_papers_knowledge_file_id` (`knowledge_file_id`),
  KEY `idx_research_papers_paper_identifier` (`paper_identifier`),
  CONSTRAINT `fk_research_papers_task_id`
    FOREIGN KEY (`task_id`) REFERENCES `research_tasks` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_research_papers_workspace_id`
    FOREIGN KEY (`workspace_id`) REFERENCES `research_workspaces` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_research_papers_knowledge_file_id`
    FOREIGN KEY (`knowledge_file_id`) REFERENCES `knowledge_files` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `extracted_papers` (
  `id` CHAR(36) NOT NULL,
  `paper_id` CHAR(36) NOT NULL,
  `task_id` CHAR(36) NOT NULL,
  `core_problem` LONGTEXT DEFAULT NULL,
  `key_methodology_name` VARCHAR(512) DEFAULT NULL,
  `key_methodology_principle` LONGTEXT DEFAULT NULL,
  `key_methodology_novelty` LONGTEXT DEFAULT NULL,
  `datasets_json` JSON DEFAULT NULL,
  `evaluation_metrics_json` JSON DEFAULT NULL,
  `main_results` LONGTEXT DEFAULT NULL,
  `limitations` LONGTEXT DEFAULT NULL,
  `contributions_json` JSON DEFAULT NULL,
  `extracted_json` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_extracted_papers_paper_id` (`paper_id`),
  KEY `idx_extracted_papers_task_id` (`task_id`),
  CONSTRAINT `fk_extracted_papers_paper_id`
    FOREIGN KEY (`paper_id`) REFERENCES `research_papers` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_extracted_papers_task_id`
    FOREIGN KEY (`task_id`) REFERENCES `research_tasks` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `analysis_clusters` (
  `id` CHAR(36) NOT NULL,
  `task_id` CHAR(36) NOT NULL,
  `cluster_name` VARCHAR(255) NOT NULL,
  `theme_description` LONGTEXT DEFAULT NULL,
  `keywords_json` JSON DEFAULT NULL,
  `paper_count` INT NOT NULL DEFAULT 0,
  `cluster_order` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_analysis_clusters_task_id` (`task_id`),
  KEY `idx_analysis_clusters_order` (`task_id`, `cluster_order`),
  CONSTRAINT `fk_analysis_clusters_task_id`
    FOREIGN KEY (`task_id`) REFERENCES `research_tasks` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `analysis_cluster_papers` (
  `id` CHAR(36) NOT NULL,
  `cluster_id` CHAR(36) NOT NULL,
  `paper_id` CHAR(36) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_analysis_cluster_papers` (`cluster_id`, `paper_id`),
  CONSTRAINT `fk_analysis_cluster_papers_cluster_id`
    FOREIGN KEY (`cluster_id`) REFERENCES `analysis_clusters` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_analysis_cluster_papers_paper_id`
    FOREIGN KEY (`paper_id`) REFERENCES `research_papers` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `analysis_reports` (
  `id` CHAR(36) NOT NULL,
  `task_id` CHAR(36) NOT NULL,
  `cluster_id` CHAR(36) DEFAULT NULL,
  `report_type` VARCHAR(32) NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `content_markdown` LONGTEXT DEFAULT NULL,
  `content_json` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_analysis_reports_task_id` (`task_id`),
  KEY `idx_analysis_reports_cluster_id` (`cluster_id`),
  CONSTRAINT `fk_analysis_reports_task_id`
    FOREIGN KEY (`task_id`) REFERENCES `research_tasks` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_analysis_reports_cluster_id`
    FOREIGN KEY (`cluster_id`) REFERENCES `analysis_clusters` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `writing_outlines` (
  `id` CHAR(36) NOT NULL,
  `task_id` CHAR(36) NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `outline_markdown` LONGTEXT DEFAULT NULL,
  `outline_json` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_writing_outlines_task_id` (`task_id`),
  CONSTRAINT `fk_writing_outlines_task_id`
    FOREIGN KEY (`task_id`) REFERENCES `research_tasks` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `writing_sections` (
  `id` CHAR(36) NOT NULL,
  `task_id` CHAR(36) NOT NULL,
  `outline_id` CHAR(36) DEFAULT NULL,
  `section_key` VARCHAR(128) NOT NULL,
  `section_title` VARCHAR(255) NOT NULL,
  `section_order` INT NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `review_status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `content_markdown` LONGTEXT DEFAULT NULL,
  `review_notes` LONGTEXT DEFAULT NULL,
  `sources_json` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_writing_sections_task_order` (`task_id`, `section_order`),
  KEY `idx_writing_sections_outline_id` (`outline_id`),
  KEY `idx_writing_sections_status` (`status`),
  CONSTRAINT `fk_writing_sections_task_id`
    FOREIGN KEY (`task_id`) REFERENCES `research_tasks` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_writing_sections_outline_id`
    FOREIGN KEY (`outline_id`) REFERENCES `writing_outlines` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `report_artifacts` (
  `id` CHAR(36) NOT NULL,
  `task_id` CHAR(36) NOT NULL,
  `workspace_id` CHAR(36) NOT NULL,
  `artifact_type` VARCHAR(32) NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `object_key` VARCHAR(512) DEFAULT NULL,
  `content_markdown` LONGTEXT DEFAULT NULL,
  `metadata_json` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_report_artifacts_task_id` (`task_id`),
  KEY `idx_report_artifacts_workspace_id` (`workspace_id`),
  CONSTRAINT `fk_report_artifacts_task_id`
    FOREIGN KEY (`task_id`) REFERENCES `research_tasks` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_report_artifacts_workspace_id`
    FOREIGN KEY (`workspace_id`) REFERENCES `research_workspaces` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `topic_exploration_packages` (
  `id` CHAR(36) NOT NULL,
  `workspace_id` CHAR(36) NOT NULL,
  `task_id` CHAR(36) NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `summary` LONGTEXT DEFAULT NULL,
  `package_json` JSON DEFAULT NULL,
  `report_markdown` LONGTEXT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_topic_exploration_packages_workspace_id` (`workspace_id`),
  KEY `idx_topic_exploration_packages_task_id` (`task_id`),
  CONSTRAINT `fk_topic_exploration_packages_workspace_id`
    FOREIGN KEY (`workspace_id`) REFERENCES `research_workspaces` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_topic_exploration_packages_task_id`
    FOREIGN KEY (`task_id`) REFERENCES `research_tasks` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `citation_evidences` (
  `id` CHAR(36) NOT NULL,
  `message_id` CHAR(36) NOT NULL,
  `knowledge_file_id` CHAR(36) DEFAULT NULL,
  `knowledge_chunk_id` CHAR(36) DEFAULT NULL,
  `research_paper_id` CHAR(36) DEFAULT NULL,
  `citation_level` VARCHAR(32) NOT NULL,
  `label` VARCHAR(255) DEFAULT NULL,
  `locator_json` JSON DEFAULT NULL,
  `snippet_text` LONGTEXT DEFAULT NULL,
  `confidence_score` DECIMAL(5,4) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_citation_evidences_message_id` (`message_id`),
  KEY `idx_citation_evidences_knowledge_file_id` (`knowledge_file_id`),
  KEY `idx_citation_evidences_knowledge_chunk_id` (`knowledge_chunk_id`),
  KEY `idx_citation_evidences_research_paper_id` (`research_paper_id`),
  CONSTRAINT `fk_citation_evidences_message_id`
    FOREIGN KEY (`message_id`) REFERENCES `messages` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_citation_evidences_knowledge_file_id`
    FOREIGN KEY (`knowledge_file_id`) REFERENCES `knowledge_files` (`id`)
    ON DELETE SET NULL,
  CONSTRAINT `fk_citation_evidences_knowledge_chunk_id`
    FOREIGN KEY (`knowledge_chunk_id`) REFERENCES `knowledge_chunks` (`id`)
    ON DELETE SET NULL,
  CONSTRAINT `fk_citation_evidences_research_paper_id`
    FOREIGN KEY (`research_paper_id`) REFERENCES `research_papers` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
