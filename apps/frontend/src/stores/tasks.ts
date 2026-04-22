import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ResearchTaskDTO, TaskDetailCardDTO, TaskMetricDTO } from '../types/tasks'
import { getTasksOverview } from '../apis/tasks'

export const useTasksStore = defineStore('tasks', () => {
  const metrics = ref<TaskMetricDTO[]>([])
  const tasks = ref<ResearchTaskDTO[]>([])
  const railCards = ref<TaskDetailCardDTO[]>([])

  async function load() {
    const data = await getTasksOverview()
    metrics.value = data.metrics
    tasks.value = data.tasks
    railCards.value = data.rail
  }

  return {
    metrics,
    tasks,
    railCards,
    load,
  }
})
