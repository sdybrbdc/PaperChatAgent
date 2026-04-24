import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { AgentRunDTO, AgentWorkflowDTO, AgentWorkflowNodeDTO } from '../types/agents'
import {
  createAgentRun,
  getAgentRun,
  getAgentWorkflow,
  getAgentWorkflows,
  saveAgentNodeConfig,
} from '../apis/agents'

export const useAgentsStore = defineStore('agents', () => {
  const workflows = ref<AgentWorkflowDTO[]>([])
  const currentWorkflow = ref<AgentWorkflowDTO | null>(null)
  const currentRun = ref<AgentRunDTO | null>(null)
  const selectedNodeId = ref('')
  const isLoading = ref(false)
  const isSaving = ref(false)
  const isStartingRun = ref(false)
  const errorMessage = ref('')

  const selectedNode = computed(() => {
    const nodes = currentWorkflow.value?.nodes ?? []
    if (!selectedNodeId.value) return null
    for (const node of nodes) {
      if (node.id === selectedNodeId.value) return node
      const subNode = node.subNodes.find((item) => item.id === selectedNodeId.value)
      if (subNode) return subNode
    }
    return null
  })

  const nodeOptions = computed(() => currentWorkflow.value?.definition?.executors as string[] | undefined)

  async function loadWorkflows() {
    isLoading.value = true
    errorMessage.value = ''
    try {
      workflows.value = await getAgentWorkflows()
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '智能体列表加载失败'
    } finally {
      isLoading.value = false
    }
  }

  async function loadWorkflow(workflowId: string) {
    isLoading.value = true
    errorMessage.value = ''
    try {
      currentWorkflow.value = await getAgentWorkflow(workflowId)
      selectedNodeId.value = ''
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '智能体详情加载失败'
    } finally {
      isLoading.value = false
    }
  }

  function selectNode(nodeId: string) {
    selectedNodeId.value = nodeId
  }

  async function saveSelectedNodeConfig(payload: {
    executorKey: string
    fallbackExecutorKey: string
    modelSlot: string
    config: Record<string, unknown>
  }) {
    if (!currentWorkflow.value || !selectedNode.value) return
    isSaving.value = true
    errorMessage.value = ''
    try {
      const updated = await saveAgentNodeConfig(currentWorkflow.value.id, selectedNode.value.id, payload)
      currentWorkflow.value.nodes = (currentWorkflow.value.nodes ?? []).map((node) => replaceNode(node, updated))
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '节点配置保存失败'
      throw error
    } finally {
      isSaving.value = false
    }
  }

  function replaceNode(node: AgentWorkflowNodeDTO, updated: AgentWorkflowNodeDTO): AgentWorkflowNodeDTO {
    if (node.id === updated.id) return { ...node, ...updated }
    return {
      ...node,
      subNodes: node.subNodes.map((subNode) => (subNode.id === updated.id ? { ...subNode, ...updated } : subNode)),
    }
  }

  async function startRun(workflowId: string, topic: string) {
    isStartingRun.value = true
    errorMessage.value = ''
    try {
      currentRun.value = await createAgentRun(workflowId, { topic })
      return currentRun.value
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '智能体运行创建失败'
      throw error
    } finally {
      isStartingRun.value = false
    }
  }

  async function loadRun(runId: string) {
    isLoading.value = true
    errorMessage.value = ''
    try {
      currentRun.value = await getAgentRun(runId)
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '运行详情加载失败'
    } finally {
      isLoading.value = false
    }
  }

  return {
    workflows,
    currentWorkflow,
    currentRun,
    selectedNodeId,
    selectedNode,
    nodeOptions,
    isLoading,
    isSaving,
    isStartingRun,
    errorMessage,
    loadWorkflows,
    loadWorkflow,
    loadRun,
    selectNode,
    saveSelectedNodeConfig,
    startRun,
  }
})
