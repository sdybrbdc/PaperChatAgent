import { MOCK_TASK_METRICS, MOCK_TASK_RAIL, MOCK_TASKS } from '../mocks/tasks'

export async function getTasksOverviewMock() {
  return {
    metrics: MOCK_TASK_METRICS,
    tasks: MOCK_TASKS,
    rail: MOCK_TASK_RAIL,
  }
}
