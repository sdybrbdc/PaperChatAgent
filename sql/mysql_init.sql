CREATE DATABASE IF NOT EXISTS `paperchat`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `paperchat`;

SET NAMES utf8mb4;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `paperchat_dashboard_metric_snapshots`;
DROP TABLE IF EXISTS `paperchat_task_events`;
DROP TABLE IF EXISTS `paperchat_tool_invocation_logs`;
DROP TABLE IF EXISTS `paperchat_model_invocation_logs`;
DROP TABLE IF EXISTS `paperchat_model_route_configs`;
DROP TABLE IF EXISTS `paperchat_model_providers`;
DROP TABLE IF EXISTS `paperchat_skill_versions`;
DROP TABLE IF EXISTS `paperchat_skill_configs`;
DROP TABLE IF EXISTS `paperchat_mcp_tools`;
DROP TABLE IF EXISTS `paperchat_mcp_servers`;
DROP TABLE IF EXISTS `paperchat_citation_evidences`;
DROP TABLE IF EXISTS `paperchat_rag_retrieval_logs`;
DROP TABLE IF EXISTS `paperchat_rag_index_jobs`;
DROP TABLE IF EXISTS `paperchat_conversation_knowledge_bindings`;
DROP TABLE IF EXISTS `paperchat_knowledge_chunks`;
DROP TABLE IF EXISTS `paperchat_knowledge_files`;
DROP TABLE IF EXISTS `paperchat_knowledge_bases`;
DROP TABLE IF EXISTS `paperchat_task_artifacts`;
DROP TABLE IF EXISTS `paperchat_workflow_node_runs`;
DROP TABLE IF EXISTS `paperchat_workflow_runs`;
DROP TABLE IF EXISTS `paperchat_research_tasks`;
DROP TABLE IF EXISTS `paperchat_agent_node_config_overrides`;
DROP TABLE IF EXISTS `paperchat_agent_workflows`;
DROP TABLE IF EXISTS `paperchat_user_memories`;
DROP TABLE IF EXISTS `paperchat_conversation_memories`;
DROP TABLE IF EXISTS `paperchat_conversation_realtime_events`;
DROP TABLE IF EXISTS `paperchat_conversation_guidance_snapshots`;
DROP TABLE IF EXISTS `paperchat_messages`;
DROP TABLE IF EXISTS `paperchat_conversations`;
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

CREATE TABLE IF NOT EXISTS `paperchat_conversation_memories` (
  `conversation_id` VARCHAR(36) NOT NULL,
  `summary_text` TEXT NOT NULL,
  `key_points_json` JSON NOT NULL,
  `user_preferences_json` JSON NOT NULL,
  `open_questions_json` JSON NOT NULL,
  `compressed_message_count` INT NOT NULL DEFAULT 0,
  `source_message_id` VARCHAR(36) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`conversation_id`),
  CONSTRAINT `fk_paperchat_conversation_memories_conversation_id`
    FOREIGN KEY (`conversation_id`) REFERENCES `paperchat_conversations` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_user_memories` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `memory_type` VARCHAR(32) NOT NULL DEFAULT 'preference',
  `title` VARCHAR(255) NOT NULL DEFAULT '',
  `content` TEXT NOT NULL,
  `tags_json` JSON NOT NULL,
  `confidence` INT NOT NULL DEFAULT 0,
  `memory_fingerprint` VARCHAR(64) NOT NULL,
  `source_conversation_id` VARCHAR(36) DEFAULT NULL,
  `source_message_id` VARCHAR(36) DEFAULT NULL,
  `active` BOOLEAN NOT NULL DEFAULT TRUE,
  `last_observed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_user_memory_fingerprint` (`user_id`, `memory_fingerprint`),
  KEY `idx_paperchat_user_memories_user_id` (`user_id`),
  KEY `idx_paperchat_user_memories_source_conversation_id` (`source_conversation_id`),
  KEY `idx_paperchat_user_memories_last_observed_at` (`last_observed_at`),
  CONSTRAINT `fk_paperchat_user_memories_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_user_memories_source_conversation_id`
    FOREIGN KEY (`source_conversation_id`) REFERENCES `paperchat_conversations` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_agent_workflows` (
  `id` VARCHAR(36) NOT NULL,
  `slug` VARCHAR(128) NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `source_type` VARCHAR(32) NOT NULL DEFAULT 'builtin',
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `version` VARCHAR(32) NOT NULL DEFAULT '1.0.0',
  `definition_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_agent_workflows_slug` (`slug`),
  KEY `idx_paperchat_agent_workflows_slug` (`slug`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_agent_node_config_overrides` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `workflow_id` VARCHAR(36) NOT NULL,
  `node_id` VARCHAR(64) NOT NULL,
  `executor_key` VARCHAR(128) NOT NULL DEFAULT '',
  `fallback_executor_key` VARCHAR(128) NOT NULL DEFAULT '',
  `model_slot` VARCHAR(64) NOT NULL DEFAULT 'conversation_model',
  `config_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_agent_node_config_user_workflow_node` (`user_id`, `workflow_id`, `node_id`),
  KEY `idx_paperchat_agent_node_config_user_id` (`user_id`),
  KEY `idx_paperchat_agent_node_config_workflow_id` (`workflow_id`),
  KEY `idx_paperchat_agent_node_config_node_id` (`node_id`),
  CONSTRAINT `fk_paperchat_agent_node_config_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_agent_node_config_workflow_id`
    FOREIGN KEY (`workflow_id`) REFERENCES `paperchat_agent_workflows` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_research_tasks` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `conversation_id` VARCHAR(36) DEFAULT NULL,
  `workflow_id` VARCHAR(36) NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `current_node` VARCHAR(64) NOT NULL DEFAULT '',
  `progress` INT NOT NULL DEFAULT 0,
  `summary` TEXT NOT NULL,
  `failed_reason` TEXT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `completed_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_research_tasks_user_id` (`user_id`),
  KEY `idx_paperchat_research_tasks_conversation_id` (`conversation_id`),
  KEY `idx_paperchat_research_tasks_workflow_id` (`workflow_id`),
  KEY `idx_paperchat_research_tasks_status` (`status`),
  CONSTRAINT `fk_paperchat_research_tasks_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_research_tasks_conversation_id`
    FOREIGN KEY (`conversation_id`) REFERENCES `paperchat_conversations` (`id`)
    ON DELETE SET NULL,
  CONSTRAINT `fk_paperchat_research_tasks_workflow_id`
    FOREIGN KEY (`workflow_id`) REFERENCES `paperchat_agent_workflows` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_workflow_runs` (
  `id` VARCHAR(36) NOT NULL,
  `task_id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `conversation_id` VARCHAR(36) DEFAULT NULL,
  `workflow_id` VARCHAR(36) NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `current_node` VARCHAR(64) NOT NULL DEFAULT '',
  `input_json` JSON NOT NULL,
  `output_json` JSON NOT NULL,
  `checkpoint_json` JSON NOT NULL,
  `error_json` JSON NOT NULL,
  `started_at` DATETIME DEFAULT NULL,
  `completed_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_workflow_runs_task_id` (`task_id`),
  KEY `idx_paperchat_workflow_runs_user_id` (`user_id`),
  KEY `idx_paperchat_workflow_runs_conversation_id` (`conversation_id`),
  KEY `idx_paperchat_workflow_runs_workflow_id` (`workflow_id`),
  KEY `idx_paperchat_workflow_runs_status` (`status`),
  CONSTRAINT `fk_paperchat_workflow_runs_task_id`
    FOREIGN KEY (`task_id`) REFERENCES `paperchat_research_tasks` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_workflow_runs_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_workflow_runs_conversation_id`
    FOREIGN KEY (`conversation_id`) REFERENCES `paperchat_conversations` (`id`)
    ON DELETE SET NULL,
  CONSTRAINT `fk_paperchat_workflow_runs_workflow_id`
    FOREIGN KEY (`workflow_id`) REFERENCES `paperchat_agent_workflows` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_workflow_node_runs` (
  `id` VARCHAR(36) NOT NULL,
  `workflow_run_id` VARCHAR(36) NOT NULL,
  `node_id` VARCHAR(64) NOT NULL,
  `parent_node_id` VARCHAR(64) NOT NULL DEFAULT '',
  `title` VARCHAR(255) NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `detail` TEXT NOT NULL,
  `progress` INT NOT NULL DEFAULT 0,
  `input_json` JSON NOT NULL,
  `output_json` JSON NOT NULL,
  `metadata_json` JSON NOT NULL,
  `error_text` TEXT NOT NULL,
  `sort_order` INT NOT NULL DEFAULT 0,
  `started_at` DATETIME DEFAULT NULL,
  `completed_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_workflow_node_run` (`workflow_run_id`, `node_id`),
  KEY `idx_paperchat_workflow_node_runs_workflow_run_id` (`workflow_run_id`),
  KEY `idx_paperchat_workflow_node_runs_node_id` (`node_id`),
  KEY `idx_paperchat_workflow_node_runs_status` (`status`),
  CONSTRAINT `fk_paperchat_workflow_node_runs_run_id`
    FOREIGN KEY (`workflow_run_id`) REFERENCES `paperchat_workflow_runs` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_task_artifacts` (
  `id` VARCHAR(36) NOT NULL,
  `task_id` VARCHAR(36) NOT NULL,
  `workflow_run_id` VARCHAR(36) NOT NULL,
  `artifact_type` VARCHAR(64) NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `content_text` TEXT NOT NULL,
  `metadata_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_task_artifacts_task_id` (`task_id`),
  KEY `idx_paperchat_task_artifacts_workflow_run_id` (`workflow_run_id`),
  KEY `idx_paperchat_task_artifacts_artifact_type` (`artifact_type`),
  CONSTRAINT `fk_paperchat_task_artifacts_task_id`
    FOREIGN KEY (`task_id`) REFERENCES `paperchat_research_tasks` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_task_artifacts_workflow_run_id`
    FOREIGN KEY (`workflow_run_id`) REFERENCES `paperchat_workflow_runs` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_knowledge_bases` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `file_count` INT NOT NULL DEFAULT 0,
  `indexed_file_count` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_knowledge_bases_user_id` (`user_id`),
  KEY `idx_paperchat_knowledge_bases_status` (`status`),
  CONSTRAINT `fk_paperchat_knowledge_bases_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_knowledge_files` (
  `id` VARCHAR(36) NOT NULL,
  `knowledge_base_id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `source_type` VARCHAR(32) NOT NULL DEFAULT 'upload',
  `title` VARCHAR(512) NOT NULL,
  `filename` VARCHAR(512) NOT NULL DEFAULT '',
  `mime_type` VARCHAR(128) NOT NULL DEFAULT '',
  `source_url` VARCHAR(1024) NOT NULL DEFAULT '',
  `object_key` VARCHAR(512) NOT NULL DEFAULT '',
  `parsed_text_object_key` VARCHAR(512) NOT NULL DEFAULT '',
  `parser_status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `index_status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `chunk_count` INT NOT NULL DEFAULT 0,
  `metadata_json` JSON NOT NULL,
  `error_text` TEXT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_knowledge_files_base_id` (`knowledge_base_id`),
  KEY `idx_paperchat_knowledge_files_user_id` (`user_id`),
  KEY `idx_paperchat_knowledge_files_parser_status` (`parser_status`),
  KEY `idx_paperchat_knowledge_files_index_status` (`index_status`),
  CONSTRAINT `fk_paperchat_knowledge_files_base_id`
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `paperchat_knowledge_bases` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_knowledge_files_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_knowledge_chunks` (
  `id` VARCHAR(36) NOT NULL,
  `knowledge_base_id` VARCHAR(36) NOT NULL,
  `knowledge_file_id` VARCHAR(36) NOT NULL,
  `chunk_index` INT NOT NULL,
  `content` TEXT NOT NULL,
  `content_hash` VARCHAR(64) NOT NULL DEFAULT '',
  `page_no` INT DEFAULT NULL,
  `section_title` VARCHAR(255) NOT NULL DEFAULT '',
  `vector_collection` VARCHAR(255) NOT NULL DEFAULT '',
  `vector_doc_id` VARCHAR(255) NOT NULL DEFAULT '',
  `token_count` INT NOT NULL DEFAULT 0,
  `locator_json` JSON NOT NULL,
  `metadata_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_knowledge_chunk_file_index` (`knowledge_file_id`, `chunk_index`),
  KEY `idx_paperchat_knowledge_chunks_base_id` (`knowledge_base_id`),
  KEY `idx_paperchat_knowledge_chunks_file_id` (`knowledge_file_id`),
  KEY `idx_paperchat_knowledge_chunks_vector_doc_id` (`vector_doc_id`),
  CONSTRAINT `fk_paperchat_knowledge_chunks_base_id`
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `paperchat_knowledge_bases` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_knowledge_chunks_file_id`
    FOREIGN KEY (`knowledge_file_id`) REFERENCES `paperchat_knowledge_files` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_conversation_knowledge_bindings` (
  `id` VARCHAR(36) NOT NULL,
  `conversation_id` VARCHAR(36) NOT NULL,
  `knowledge_base_id` VARCHAR(36) NOT NULL,
  `binding_type` VARCHAR(32) NOT NULL DEFAULT 'manual',
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_conversation_knowledge_binding` (`conversation_id`, `knowledge_base_id`),
  KEY `idx_paperchat_ckb_base_id` (`knowledge_base_id`),
  CONSTRAINT `fk_paperchat_ckb_conversation_id`
    FOREIGN KEY (`conversation_id`) REFERENCES `paperchat_conversations` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_ckb_base_id`
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `paperchat_knowledge_bases` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_rag_index_jobs` (
  `id` VARCHAR(36) NOT NULL,
  `knowledge_file_id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `stage` VARCHAR(32) NOT NULL DEFAULT 'queued',
  `progress` INT NOT NULL DEFAULT 0,
  `parser_name` VARCHAR(128) NOT NULL DEFAULT '',
  `embedding_route_key` VARCHAR(64) NOT NULL DEFAULT 'embedding',
  `error_text` TEXT NOT NULL,
  `metadata_json` JSON NOT NULL,
  `started_at` DATETIME DEFAULT NULL,
  `completed_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_rag_index_jobs_file_id` (`knowledge_file_id`),
  KEY `idx_paperchat_rag_index_jobs_user_id` (`user_id`),
  KEY `idx_paperchat_rag_index_jobs_status` (`status`),
  CONSTRAINT `fk_paperchat_rag_index_jobs_file_id`
    FOREIGN KEY (`knowledge_file_id`) REFERENCES `paperchat_knowledge_files` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_rag_index_jobs_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_rag_retrieval_logs` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `conversation_id` VARCHAR(36) DEFAULT NULL,
  `message_id` VARCHAR(36) DEFAULT NULL,
  `query_text` TEXT NOT NULL,
  `knowledge_base_ids_json` JSON NOT NULL,
  `top_k` INT NOT NULL DEFAULT 8,
  `result_count` INT NOT NULL DEFAULT 0,
  `latency_ms` INT NOT NULL DEFAULT 0,
  `results_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_rag_logs_user_id` (`user_id`),
  KEY `idx_paperchat_rag_logs_conversation_id` (`conversation_id`),
  KEY `idx_paperchat_rag_logs_created_at` (`created_at`),
  CONSTRAINT `fk_paperchat_rag_logs_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_rag_logs_conversation_id`
    FOREIGN KEY (`conversation_id`) REFERENCES `paperchat_conversations` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_citation_evidences` (
  `id` VARCHAR(36) NOT NULL,
  `message_id` VARCHAR(36) NOT NULL,
  `knowledge_file_id` VARCHAR(36) DEFAULT NULL,
  `knowledge_chunk_id` VARCHAR(36) DEFAULT NULL,
  `retrieval_log_id` VARCHAR(36) DEFAULT NULL,
  `label` VARCHAR(255) NOT NULL,
  `snippet` TEXT NOT NULL,
  `score` FLOAT NOT NULL DEFAULT 0,
  `locator_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_citations_message_id` (`message_id`),
  KEY `idx_paperchat_citations_file_id` (`knowledge_file_id`),
  KEY `idx_paperchat_citations_chunk_id` (`knowledge_chunk_id`),
  CONSTRAINT `fk_paperchat_citations_message_id`
    FOREIGN KEY (`message_id`) REFERENCES `paperchat_messages` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_citations_file_id`
    FOREIGN KEY (`knowledge_file_id`) REFERENCES `paperchat_knowledge_files` (`id`)
    ON DELETE SET NULL,
  CONSTRAINT `fk_paperchat_citations_chunk_id`
    FOREIGN KEY (`knowledge_chunk_id`) REFERENCES `paperchat_knowledge_chunks` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_mcp_servers` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `transport_type` VARCHAR(32) NOT NULL DEFAULT 'stdio',
  `command` VARCHAR(512) NOT NULL DEFAULT '',
  `args_json` JSON NOT NULL,
  `endpoint_url` VARCHAR(1024) NOT NULL DEFAULT '',
  `headers_json` JSON NOT NULL,
  `env_json` JSON NOT NULL,
  `secret_config_json` JSON NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'disabled',
  `last_health_status` VARCHAR(32) NOT NULL DEFAULT 'unknown',
  `last_checked_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_mcp_servers_user_id` (`user_id`),
  KEY `idx_paperchat_mcp_servers_status` (`status`),
  CONSTRAINT `fk_paperchat_mcp_servers_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_mcp_tools` (
  `id` VARCHAR(36) NOT NULL,
  `server_id` VARCHAR(36) NOT NULL,
  `tool_name` VARCHAR(255) NOT NULL,
  `display_name` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `input_schema_json` JSON NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `last_seen_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_mcp_tool_server_name` (`server_id`, `tool_name`),
  KEY `idx_paperchat_mcp_tools_server_id` (`server_id`),
  CONSTRAINT `fk_paperchat_mcp_tools_server_id`
    FOREIGN KEY (`server_id`) REFERENCES `paperchat_mcp_servers` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_skill_configs` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `source_type` VARCHAR(32) NOT NULL DEFAULT 'local',
  `source_uri` VARCHAR(1024) NOT NULL DEFAULT '',
  `entrypoint` VARCHAR(512) NOT NULL DEFAULT '',
  `status` VARCHAR(32) NOT NULL DEFAULT 'disabled',
  `manifest_json` JSON NOT NULL,
  `input_schema_json` JSON NOT NULL,
  `output_schema_json` JSON NOT NULL,
  `metadata_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_skill_configs_user_id` (`user_id`),
  KEY `idx_paperchat_skill_configs_status` (`status`),
  CONSTRAINT `fk_paperchat_skill_configs_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_skill_versions` (
  `id` VARCHAR(36) NOT NULL,
  `skill_id` VARCHAR(36) NOT NULL,
  `version` VARCHAR(64) NOT NULL,
  `manifest_json` JSON NOT NULL,
  `checksum` VARCHAR(128) NOT NULL DEFAULT '',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_skill_version` (`skill_id`, `version`),
  CONSTRAINT `fk_paperchat_skill_versions_skill_id`
    FOREIGN KEY (`skill_id`) REFERENCES `paperchat_skill_configs` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_model_providers` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `provider_key` VARCHAR(128) NOT NULL,
  `display_name` VARCHAR(255) NOT NULL,
  `base_url` VARCHAR(1024) NOT NULL DEFAULT '',
  `api_key_secret_ref` VARCHAR(512) NOT NULL DEFAULT '',
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `metadata_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_model_provider_user_key` (`user_id`, `provider_key`),
  KEY `idx_paperchat_model_providers_user_id` (`user_id`),
  CONSTRAINT `fk_paperchat_model_providers_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_model_route_configs` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `route_key` VARCHAR(64) NOT NULL,
  `provider_id` VARCHAR(36) NOT NULL,
  `model_name` VARCHAR(255) NOT NULL,
  `temperature` FLOAT DEFAULT NULL,
  `max_tokens` INT DEFAULT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `config_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_model_route_user_key` (`user_id`, `route_key`),
  KEY `idx_paperchat_model_routes_user_id` (`user_id`),
  KEY `idx_paperchat_model_routes_provider_id` (`provider_id`),
  CONSTRAINT `fk_paperchat_model_routes_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_model_routes_provider_id`
    FOREIGN KEY (`provider_id`) REFERENCES `paperchat_model_providers` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_model_invocation_logs` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `conversation_id` VARCHAR(36) DEFAULT NULL,
  `task_id` VARCHAR(36) DEFAULT NULL,
  `workflow_run_id` VARCHAR(36) DEFAULT NULL,
  `route_key` VARCHAR(64) NOT NULL,
  `provider_key` VARCHAR(128) NOT NULL,
  `model_name` VARCHAR(255) NOT NULL,
  `input_tokens` INT NOT NULL DEFAULT 0,
  `output_tokens` INT NOT NULL DEFAULT 0,
  `latency_ms` INT NOT NULL DEFAULT 0,
  `status` VARCHAR(32) NOT NULL DEFAULT 'success',
  `error_code` VARCHAR(128) NOT NULL DEFAULT '',
  `metadata_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_model_logs_user_id` (`user_id`),
  KEY `idx_paperchat_model_logs_route_key` (`route_key`),
  KEY `idx_paperchat_model_logs_created_at` (`created_at`),
  KEY `idx_paperchat_model_logs_status` (`status`),
  CONSTRAINT `fk_paperchat_model_logs_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_tool_invocation_logs` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `conversation_id` VARCHAR(36) DEFAULT NULL,
  `task_id` VARCHAR(36) DEFAULT NULL,
  `capability_id` VARCHAR(255) NOT NULL,
  `capability_type` VARCHAR(32) NOT NULL,
  `input_json` JSON NOT NULL,
  `output_json` JSON NOT NULL,
  `latency_ms` INT NOT NULL DEFAULT 0,
  `status` VARCHAR(32) NOT NULL DEFAULT 'success',
  `error_text` TEXT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_tool_logs_user_id` (`user_id`),
  KEY `idx_paperchat_tool_logs_conversation_id` (`conversation_id`),
  KEY `idx_paperchat_tool_logs_task_id` (`task_id`),
  KEY `idx_paperchat_tool_logs_capability_type` (`capability_type`),
  KEY `idx_paperchat_tool_logs_created_at` (`created_at`),
  KEY `idx_paperchat_tool_logs_status` (`status`),
  CONSTRAINT `fk_paperchat_tool_logs_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_task_events` (
  `id` VARCHAR(36) NOT NULL,
  `task_id` VARCHAR(36) NOT NULL,
  `workflow_run_id` VARCHAR(36) DEFAULT NULL,
  `node_id` VARCHAR(64) NOT NULL DEFAULT '',
  `event_type` VARCHAR(64) NOT NULL,
  `payload_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_task_events_task_id` (`task_id`),
  KEY `idx_paperchat_task_events_created_at` (`created_at`),
  CONSTRAINT `fk_paperchat_task_events_task_id`
    FOREIGN KEY (`task_id`) REFERENCES `paperchat_research_tasks` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paperchat_dashboard_metric_snapshots` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `metric_key` VARCHAR(128) NOT NULL,
  `metric_value` FLOAT NOT NULL DEFAULT 0,
  `dimension_json` JSON NOT NULL,
  `recorded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_metric_snapshots_user_key` (`user_id`, `metric_key`),
  KEY `idx_paperchat_metric_snapshots_recorded_at` (`recorded_at`),
  CONSTRAINT `fk_paperchat_metric_snapshots_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
