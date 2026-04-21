export interface WorkflowNodeDTO {
  id: string
  title: string
  description: string
  tone?: 'default' | 'warn' | 'accent'
}

export interface WorkflowSideCardDTO {
  title: string
  lines: string[]
}
