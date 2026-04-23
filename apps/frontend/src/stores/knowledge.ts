import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { KnowledgeBaseDTO, KnowledgeSideCardDTO } from '../types/knowledge'
import { getKnowledgeOverview } from '../apis/knowledge'

export const useKnowledgeStore = defineStore('knowledge', () => {
  const library = ref<KnowledgeBaseDTO | null>(null)
  const railCards = ref<KnowledgeSideCardDTO[]>([])

  async function load() {
    const data = await getKnowledgeOverview()
    library.value = data.library
    railCards.value = data.rail
  }

  return {
    library,
    railCards,
    load,
  }
})
