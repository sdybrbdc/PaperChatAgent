import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { KnowledgeBaseDTO, KnowledgeSideCardDTO } from '../types/knowledge'
import { getKnowledgeOverview } from '../apis/knowledge'

export const useKnowledgeStore = defineStore('knowledge', () => {
  const globalBase = ref<KnowledgeBaseDTO | null>(null)
  const privateBase = ref<KnowledgeBaseDTO | null>(null)
  const railCards = ref<KnowledgeSideCardDTO[]>([])

  async function load() {
    const data = await getKnowledgeOverview()
    globalBase.value = data.global
    privateBase.value = data.private
    railCards.value = data.rail
  }

  return {
    globalBase,
    privateBase,
    railCards,
    load,
  }
})
