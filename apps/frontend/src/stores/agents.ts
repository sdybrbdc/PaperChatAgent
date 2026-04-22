import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { WorkflowNodeDTO, WorkflowSideCardDTO } from '../types/agents'
import { getWorkflowDefinition } from '../apis/agents'

export const useAgentsStore = defineStore('agents', () => {
  const nodes = ref<WorkflowNodeDTO[]>([])
  const railCards = ref<WorkflowSideCardDTO[]>([])

  async function load() {
    const data = await getWorkflowDefinition()
    nodes.value = data.nodes
    railCards.value = data.rail
  }

  return {
    nodes,
    railCards,
    load,
  }
})
