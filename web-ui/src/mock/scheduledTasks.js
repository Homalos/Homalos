/**
 * 任务调度器数据（硬编码）
 */
export const scheduledTasksData = [
  {
    id: 1,
    name: "每日数据备份",
    type: "daily",
    config: { time: "23:00" },
    status: "enabled",
    createTime: "2025-10-01 10:30:00",
    lastExecuteTime: "2025-10-08 23:00:00",
    executionHistory: [
      { time: "2025-10-08 23:00:00", status: "success", duration: "2.5s" },
      { time: "2025-10-07 23:00:00", status: "success", duration: "2.3s" },
      { time: "2025-10-06 23:00:00", status: "failed", duration: "0.5s", error: "网络连接失败" }
    ]
  },
  {
    id: 2,
    name: "周报生成",
    type: "weekday",
    config: { time: "09:00", dayOfWeek: ["周一"] },
    status: "enabled",
    createTime: "2025-09-25 15:20:00",
    lastExecuteTime: "2025-10-07 09:00:00",
    executionHistory: [
      { time: "2025-10-07 09:00:00", status: "success", duration: "5.2s" }
    ]
  },
  {
    id: 3,
    name: "实时监控检查",
    type: "minute",
    config: {},
    status: "enabled",
    createTime: "2025-10-08 20:00:00",
    lastExecuteTime: "2025-10-10 00:05:00",
    executionHistory: []
  },
  {
    id: 4,
    name: "月度报表",
    type: "monthly",
    config: { time: "08:00", monthDay: ["01", "15"] },
    status: "disabled",
    createTime: "2025-09-20 11:00:00",
    lastExecuteTime: "2025-10-01 08:00:00",
    executionHistory: [
      { time: "2025-10-01 08:00:00", status: "success", duration: "8.5s" }
    ]
  },
  {
    id: 5,
    name: "临时数据清理",
    type: "once",
    config: { dateTime: "2025-10-10 02:00:00" },
    status: "disabled",
    createTime: "2025-10-09 18:30:00",
    lastExecuteTime: null,
    executionHistory: []
  }
]

